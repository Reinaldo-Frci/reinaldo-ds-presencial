import re

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .models import EPI, Colaborador, Emprestimo, ItemEmprestimo, Usuario

admin_required = user_passes_test(
    lambda u: u.is_authenticated and u.eh_admin, login_url='login')


@login_required
def dashboard(request):
    Emprestimo.atualizar_atrasados()
    epis = EPI.objects.filter(ativo=True)
    return render(request, 'core/dashboard.html', {
        'total_ativos': Emprestimo.objects.filter(status='ATIVO').count(),
        'total_atrasados': Emprestimo.objects.filter(status='ATRASADO').count(),
        'cas_a_vencer': [e for e in epis if e.ca_a_vencer or e.ca_vencido],
        'estoque_baixo': [e for e in epis if e.estoque_baixo],
        'ultimos_emprestimos': Emprestimo.objects.select_related('colaborador')[:8],
    })


@login_required
def colaborador_lista(request):
    busca = request.GET.get('q', '').strip()
    setor = request.GET.get('setor', '').strip()
    colaboradores = Colaborador.objects.all()
    if busca:
        colaboradores = colaboradores.filter(
            Q(nome__icontains=busca) | Q(matricula__icontains=busca))
    if setor:
        colaboradores = colaboradores.filter(setor=setor)
    setores = (Colaborador.objects.values_list('setor', flat=True)
               .distinct().order_by('setor'))
    return render(request, 'core/colaborador_lista.html', {
        'colaboradores': colaboradores, 'busca': busca,
        'setores': setores, 'setor_sel': setor,
    })


@login_required
def colaborador_form(request, pk=None):
    colaborador = get_object_or_404(Colaborador, pk=pk) if pk else None
    erros = []
    dados = {}
    if colaborador:
        dados = {
            'matricula': colaborador.matricula,
            'nome': colaborador.nome,
            'cpf': colaborador.cpf,
            'data_nascimento': colaborador.data_nascimento.isoformat() if colaborador.data_nascimento else '',
            'cargo': colaborador.cargo,
            'setor': colaborador.setor,
            'telefone': colaborador.telefone,
            'email': colaborador.email,
        }
    if request.method == 'POST':
        dados = request.POST
        matricula = dados.get('matricula', '').strip()
        nome = dados.get('nome', '').strip()
        cpf_digitos = re.sub(r'\D', '', dados.get('cpf', ''))
        cargo = dados.get('cargo', '').strip()
        setor = dados.get('setor', '').strip()

        if not (matricula and nome and cpf_digitos and cargo and setor):
            erros.append('Preencha todos os campos obrigatórios (*).')

        cpf = ''
        if cpf_digitos:
            if len(cpf_digitos) != 11:
                erros.append('O CPF deve conter 11 dígitos.')
            else:
                cpf = '%s.%s.%s-%s' % (cpf_digitos[:3], cpf_digitos[3:6],
                                       cpf_digitos[6:9], cpf_digitos[9:])

        if matricula and Colaborador.objects.filter(
                matricula=matricula).exclude(pk=pk).exists():
            erros.append('Já existe um colaborador com a matrícula %s.' % matricula)
        if cpf and Colaborador.objects.filter(cpf=cpf).exclude(pk=pk).exists():
            erros.append('Já existe um colaborador com o CPF %s.' % cpf)

        if not erros:
            if colaborador is None:
                colaborador = Colaborador()
            colaborador.matricula = matricula
            colaborador.nome = nome
            colaborador.cpf = cpf
            colaborador.data_nascimento = dados.get('data_nascimento') or None
            colaborador.cargo = cargo
            colaborador.setor = setor
            colaborador.telefone = dados.get('telefone', '').strip()
            colaborador.email = dados.get('email', '').strip()
            colaborador.save()
            acao = 'atualizado' if pk else 'cadastrado'
            messages.success(request, 'Colaborador "%s" %s com sucesso.' % (nome, acao))
            return redirect('colaborador_lista')

    return render(request, 'core/colaborador_form.html', {
        'colaborador': colaborador, 'erros': erros, 'dados': dados,
    })


@login_required
def colaborador_toggle(request, pk):
    if request.method == 'POST':
        colaborador = get_object_or_404(Colaborador, pk=pk)
        colaborador.ativo = not colaborador.ativo
        colaborador.save()
        estado = 'reativado' if colaborador.ativo else 'inativado'
        messages.success(request, 'Colaborador "%s" %s.' % (colaborador.nome, estado))
    return redirect('colaborador_lista')


@login_required
def epi_lista(request):
    busca = request.GET.get('q', '').strip()
    epis = EPI.objects.all()
    if busca:
        epis = epis.filter(Q(nome__icontains=busca) | Q(ca_numero__icontains=busca))
    return render(request, 'core/epi_lista.html', {'epis': epis, 'busca': busca})


@login_required
def epi_form(request, pk=None):
    epi = get_object_or_404(EPI, pk=pk) if pk else None
    erros = []
    dados = {'qtd_estoque': '0', 'qtd_minima': '5'}
    if epi:
        dados = {
            'nome': epi.nome,
            'descricao': epi.descricao,
            'categoria': epi.categoria,
            'ca_numero': epi.ca_numero,
            'ca_validade': epi.ca_validade.isoformat(),
            'tamanho': epi.tamanho,
            'qtd_estoque': str(epi.qtd_estoque),
            'qtd_minima': str(epi.qtd_minima),
        }
    if request.method == 'POST':
        dados = request.POST
        nome = dados.get('nome', '').strip()
        categoria = dados.get('categoria', '')
        ca_numero = dados.get('ca_numero', '').strip()
        ca_validade = dados.get('ca_validade', '')

        if not (nome and categoria and ca_numero and ca_validade):
            erros.append('Preencha todos os campos obrigatórios (*).')

        qtd_estoque, qtd_minima = 0, 5
        try:
            qtd_estoque = int(dados.get('qtd_estoque') or 0)
            qtd_minima = int(dados.get('qtd_minima') or 5)
            if qtd_estoque < 0 or qtd_minima < 0:
                erros.append('As quantidades não podem ser negativas.')
        except ValueError:
            erros.append('As quantidades devem ser números inteiros.')

        if not erros:
            if epi is None:
                epi = EPI()
            epi.nome = nome
            epi.descricao = dados.get('descricao', '').strip()
            epi.categoria = categoria
            epi.ca_numero = ca_numero
            epi.ca_validade = ca_validade
            epi.tamanho = dados.get('tamanho', '').strip()
            epi.qtd_estoque = qtd_estoque
            epi.qtd_minima = qtd_minima
            epi.save()
            acao = 'atualizado' if pk else 'cadastrado'
            messages.success(request, 'EPI "%s" %s com sucesso.' % (nome, acao))
            return redirect('epi_lista')

    return render(request, 'core/epi_form.html', {
        'epi': epi, 'erros': erros, 'dados': dados,
        'categorias': EPI.Categoria.choices,
    })


@login_required
def epi_toggle(request, pk):
    if request.method == 'POST':
        epi = get_object_or_404(EPI, pk=pk)
        epi.ativo = not epi.ativo
        epi.save()
        estado = 'reativado' if epi.ativo else 'inativado'
        messages.success(request, 'EPI "%s" %s.' % (epi.nome, estado))
    return redirect('epi_lista')


@login_required
def emprestimo_lista(request):
    Emprestimo.atualizar_atrasados()
    busca = request.GET.get('q', '').strip()
    status = request.GET.get('status', '').strip()
    emprestimos = Emprestimo.objects.select_related('colaborador', 'usuario')
    if busca:
        emprestimos = emprestimos.filter(colaborador__nome__icontains=busca)
    if status:
        emprestimos = emprestimos.filter(status=status)
    return render(request, 'core/emprestimo_lista.html', {
        'emprestimos': emprestimos, 'busca': busca,
        'status_sel': status, 'status_choices': Emprestimo.Status.choices,
    })


@login_required
def emprestimo_novo(request):
    erros = []
    if request.method == 'POST':
        dados = request.POST
        colaborador_id = dados.get('colaborador', '')
        data_prevista = dados.get('data_prevista_devolucao', '')

        if not colaborador_id or not data_prevista:
            erros.append('Selecione o colaborador e informe a data prevista de devolução.')

        itens = []
        ids_usados = []
        for i in range(1, 4):
            epi_id = dados.get('epi_%d' % i, '')
            if not epi_id:
                continue
            epi = get_object_or_404(EPI, pk=epi_id)
            try:
                qtd = int(dados.get('qtd_%d' % i) or 1)
            except ValueError:
                qtd = 0
            if qtd < 1:
                erros.append('Informe uma quantidade válida para "%s".' % epi.nome)
            elif epi_id in ids_usados:
                erros.append('O EPI "%s" foi adicionado mais de uma vez. '
                             'Some as quantidades em uma única linha.' % epi.nome)
            elif epi.ca_vencido:
                erros.append('O CA do EPI "%s" está vencido (%s). Empréstimo '
                             'bloqueado pela NR-6.'
                             % (epi.nome, epi.ca_validade.strftime('%d/%m/%Y')))
            elif qtd > epi.qtd_estoque:
                erros.append('Estoque insuficiente para "%s": disponível %d, '
                             'solicitado %d.' % (epi.nome, epi.qtd_estoque, qtd))
            else:
                ids_usados.append(epi_id)
                itens.append((epi, qtd))

        if not itens and not erros:
            erros.append('Adicione pelo menos um EPI ao empréstimo.')

        if not erros:
            with transaction.atomic():
                emprestimo = Emprestimo.objects.create(
                    colaborador_id=colaborador_id,
                    usuario=request.user,
                    data_prevista_devolucao=data_prevista,
                    observacao=dados.get('observacao', '').strip())
                for epi, qtd in itens:
                    ItemEmprestimo.objects.create(
                        emprestimo=emprestimo, epi=epi, quantidade=qtd)
                    epi.qtd_estoque -= qtd
                    epi.save()
            messages.success(request, 'Empréstimo nº %d registrado para %s. '
                             'Estoque atualizado.'
                             % (emprestimo.pk, emprestimo.colaborador.nome))
            return redirect('emprestimo_ficha', pk=emprestimo.pk)

    return render(request, 'core/emprestimo_form.html', {
        'colaboradores': Colaborador.objects.filter(ativo=True),
        'epis': EPI.objects.filter(ativo=True),
        'erros': erros, 'dados': request.POST,
    })


@login_required
def emprestimo_devolucao(request, pk):
    emprestimo = get_object_or_404(Emprestimo, pk=pk)
    itens = emprestimo.itens_pendentes.select_related('epi')
    if request.method == 'POST':
        devolvidos = 0
        with transaction.atomic():
            for item in itens:
                condicao = request.POST.get('condicao_%d' % item.pk, '')
                if condicao in ItemEmprestimo.Condicao.values:
                    item.condicao_devolucao = condicao
                    item.data_devolucao = timezone.now()
                    item.save()
                    if condicao == ItemEmprestimo.Condicao.BOM_ESTADO:
                        item.epi.qtd_estoque += item.quantidade
                        item.epi.save()
                    devolvidos += 1
            if not emprestimo.itens_pendentes.exists():
                emprestimo.status = Emprestimo.Status.DEVOLVIDO
                emprestimo.save()
        if devolvidos:
            messages.success(request, '%d item(ns) devolvido(s). Itens em bom '
                             'estado retornaram ao estoque.' % devolvidos)
        else:
            messages.warning(request, 'Nenhum item selecionado para devolução.')
        return redirect('emprestimo_lista')
    return render(request, 'core/emprestimo_devolucao.html', {
        'emprestimo': emprestimo, 'itens': itens,
        'condicoes': ItemEmprestimo.Condicao.choices,
    })


@login_required
def emprestimo_ficha(request, pk):
    emprestimo = get_object_or_404(
        Emprestimo.objects.select_related('colaborador', 'usuario'), pk=pk)
    return render(request, 'core/emprestimo_ficha.html', {'emprestimo': emprestimo})


@admin_required
def usuario_lista(request):
    return render(request, 'core/usuario_lista.html', {
        'usuarios': Usuario.objects.order_by('first_name', 'username'),
    })


@admin_required
def usuario_novo(request):
    erros = []
    if request.method == 'POST':
        dados = request.POST
        nome = dados.get('nome', '').strip()
        username = dados.get('username', '').strip()
        perfil = dados.get('perfil', '')
        senha1 = dados.get('senha1', '')
        senha2 = dados.get('senha2', '')

        if not (nome and username and perfil and senha1 and senha2):
            erros.append('Preencha todos os campos obrigatórios (*).')
        if senha1 and senha2 and senha1 != senha2:
            erros.append('As senhas não conferem.')
        if senha1 and len(senha1) < 8:
            erros.append('A senha deve ter pelo menos 8 caracteres.')
        if username and Usuario.objects.filter(username=username).exists():
            erros.append('Já existe um usuário com o login "%s".' % username)

        if not erros:
            Usuario.objects.create_user(
                username=username, password=senha1, first_name=nome,
                email=dados.get('email', '').strip(), perfil=perfil)
            messages.success(request, 'Usuário "%s" cadastrado.' % username)
            return redirect('usuario_lista')

    return render(request, 'core/usuario_form.html', {
        'erros': erros, 'dados': request.POST,
        'perfis': Usuario.Perfil.choices,
    })


@login_required
def relatorios(request):
    Emprestimo.atualizar_atrasados()
    itens = ItemEmprestimo.objects.select_related(
        'epi', 'emprestimo__colaborador', 'emprestimo__usuario')

    colaborador_id = request.GET.get('colaborador', '')
    epi_id = request.GET.get('epi', '')
    inicio = request.GET.get('inicio', '')
    fim = request.GET.get('fim', '')
    if colaborador_id:
        itens = itens.filter(emprestimo__colaborador_id=colaborador_id)
    if epi_id:
        itens = itens.filter(epi_id=epi_id)
    if inicio:
        itens = itens.filter(emprestimo__data_emprestimo__date__gte=inicio)
    if fim:
        itens = itens.filter(emprestimo__data_emprestimo__date__lte=fim)

    por_colaborador = (itens.values('emprestimo__colaborador__nome')
                       .annotate(total=Sum('quantidade')).order_by('-total'))
    por_epi = (itens.values('epi__nome')
               .annotate(total=Sum('quantidade')).order_by('-total'))

    return render(request, 'core/relatorios.html', {
        'itens': itens.order_by('-emprestimo__data_emprestimo'),
        'por_colaborador': por_colaborador,
        'por_epi': por_epi,
        'colaboradores': Colaborador.objects.all(),
        'epis': EPI.objects.all(),
        'filtros': {'colaborador': colaborador_id, 'epi': epi_id,
                    'inicio': inicio, 'fim': fim},
    })
