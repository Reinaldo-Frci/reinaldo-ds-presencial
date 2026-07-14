"""
Views do Sistema de Gerenciamento de EPIs.
Cada view referencia o requisito funcional que atende (documentação Etapa 1).
"""
from datetime import timedelta

from django.contrib import messages
from django.contrib.auth.decorators import login_required, user_passes_test
from django.db import transaction
from django.db.models import Q, Sum
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone

from .forms import (ColaboradorForm, EmprestimoForm, EPIForm,
                    ItemEmprestimoFormSet, UsuarioForm)
from .models import EPI, Colaborador, Emprestimo, ItemEmprestimo, Usuario

# Somente o perfil Administrador gerencia usuários (RF03/RNF02)
admin_required = user_passes_test(
    lambda u: u.is_authenticated and u.eh_admin, login_url='login')


# ---------------------------------------------------------------- Dashboard
@login_required
def dashboard(request):
    Emprestimo.atualizar_atrasados()
    hoje = timezone.localdate()
    epis = EPI.objects.filter(ativo=True)
    contexto = {
        'total_ativos': Emprestimo.objects.filter(status='ATIVO').count(),
        'total_atrasados': Emprestimo.objects.filter(status='ATRASADO').count(),
        'cas_a_vencer': [e for e in epis if e.ca_a_vencer or e.ca_vencido],
        'estoque_baixo': [e for e in epis if e.estoque_baixo],
        'ultimos_emprestimos': (Emprestimo.objects
                                .select_related('colaborador')[:8]),
    }
    return render(request, 'core/dashboard.html', contexto)


# ------------------------------------------------------------- Colaboradores
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
    form = ColaboradorForm(request.POST or None, instance=colaborador)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        acao = 'atualizado' if pk else 'cadastrado'
        messages.success(request, f'Colaborador "{obj.nome}" {acao} com sucesso.')
        return redirect('colaborador_lista')
    return render(request, 'core/colaborador_form.html',
                  {'form': form, 'colaborador': colaborador})


@login_required
def colaborador_toggle(request, pk):
    if request.method == 'POST':
        colaborador = get_object_or_404(Colaborador, pk=pk)
        colaborador.ativo = not colaborador.ativo
        colaborador.save()
        estado = 'reativado' if colaborador.ativo else 'inativado'
        messages.success(request, f'Colaborador "{colaborador.nome}" {estado}.')
    return redirect('colaborador_lista')


# ---------------------------------------------------------------------- EPIs
@login_required
def epi_lista(request):
    """Listagem de EPIs com estoque e situação do CA (RF02/RF08)."""
    busca = request.GET.get('q', '').strip()
    epis = EPI.objects.all()
    if busca:
        epis = epis.filter(Q(nome__icontains=busca) | Q(ca_numero__icontains=busca))
    return render(request, 'core/epi_lista.html', {'epis': epis, 'busca': busca})


@login_required
def epi_form(request, pk=None):
    """Cadastro e edição de EPI (RF02)."""
    epi = get_object_or_404(EPI, pk=pk) if pk else None
    form = EPIForm(request.POST or None, instance=epi)
    if request.method == 'POST' and form.is_valid():
        obj = form.save()
        acao = 'atualizado' if pk else 'cadastrado'
        messages.success(request, f'EPI "{obj.nome}" {acao} com sucesso.')
        return redirect('epi_lista')
    return render(request, 'core/epi_form.html', {'form': form, 'epi': epi})


@login_required
def epi_toggle(request, pk):
    if request.method == 'POST':
        epi = get_object_or_404(EPI, pk=pk)
        epi.ativo = not epi.ativo
        epi.save()
        estado = 'reativado' if epi.ativo else 'inativado'
        messages.success(request, f'EPI "{epi.nome}" {estado}.')
    return redirect('epi_lista')


# ---------------------------------------------------------------- Empréstimos
@login_required
def emprestimo_lista(request):
    """Listagem de empréstimos com filtro por status e busca (RF09)."""
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
    """Registro de empréstimo com baixa automática de estoque (RF05/RF07)."""
    form = EmprestimoForm(request.POST or None)
    formset = ItemEmprestimoFormSet(request.POST or None)
    if request.method == 'POST' and form.is_valid() and formset.is_valid():
        with transaction.atomic():
            emprestimo = form.save(commit=False)
            emprestimo.usuario = request.user  # RN01: quem registrou
            emprestimo.save()
            formset.instance = emprestimo
            itens = formset.save()
            for item in itens:  # baixa de estoque
                EPI.objects.filter(pk=item.epi_id).update(
                    qtd_estoque=item.epi.qtd_estoque - item.quantidade)
        messages.success(
            request,
            f'Empréstimo nº {emprestimo.pk} registrado para '
            f'{emprestimo.colaborador.nome}. Estoque atualizado.')
        return redirect('emprestimo_ficha', pk=emprestimo.pk)
    return render(request, 'core/emprestimo_form.html',
                  {'form': form, 'formset': formset})


@login_required
def emprestimo_devolucao(request, pk):
    """Devolução dos itens: bom estado retorna ao estoque (RF06/RN03)."""
    emprestimo = get_object_or_404(Emprestimo, pk=pk)
    itens = emprestimo.itens_pendentes.select_related('epi')
    if request.method == 'POST':
        devolvidos = 0
        with transaction.atomic():
            for item in itens:
                condicao = request.POST.get(f'condicao_{item.pk}', '')
                if condicao in ItemEmprestimo.Condicao.values:
                    item.condicao_devolucao = condicao
                    item.data_devolucao = timezone.now()
                    item.save()
                    if condicao == ItemEmprestimo.Condicao.BOM_ESTADO:
                        EPI.objects.filter(pk=item.epi_id).update(
                            qtd_estoque=item.epi.qtd_estoque + item.quantidade)
                    devolvidos += 1
            if not emprestimo.itens_pendentes.exists():
                emprestimo.status = Emprestimo.Status.DEVOLVIDO
                emprestimo.save()
        if devolvidos:
            messages.success(request, f'{devolvidos} item(ns) devolvido(s). '
                             'Itens em bom estado retornaram ao estoque.')
        else:
            messages.warning(request, 'Nenhum item selecionado para devolução.')
        return redirect('emprestimo_lista')
    return render(request, 'core/emprestimo_devolucao.html', {
        'emprestimo': emprestimo, 'itens': itens,
        'condicoes': ItemEmprestimo.Condicao.choices,
    })


@login_required
def emprestimo_ficha(request, pk):
    """Ficha de entrega de EPI para impressão — registro NR-6 (RF10)."""
    emprestimo = get_object_or_404(
        Emprestimo.objects.select_related('colaborador', 'usuario'), pk=pk)
    return render(request, 'core/emprestimo_ficha.html', {'emprestimo': emprestimo})


# -------------------------------------------------------------------- Usuários
@admin_required
def usuario_lista(request):
    """Listagem de usuários do sistema — restrito ao Administrador (RF03)."""
    return render(request, 'core/usuario_lista.html',
                  {'usuarios': Usuario.objects.order_by('first_name', 'username')})


@admin_required
def usuario_novo(request):
    form = UsuarioForm(request.POST or None)
    if request.method == 'POST' and form.is_valid():
        usuario = form.save()
        messages.success(request, f'Usuário "{usuario.username}" cadastrado.')
        return redirect('usuario_lista')
    return render(request, 'core/usuario_form.html', {'form': form})


# ------------------------------------------------------------------ Relatórios
@login_required
def relatorios(request):
    """Relatórios de empréstimos por colaborador e por equipamento (bônus/RF09)."""
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
