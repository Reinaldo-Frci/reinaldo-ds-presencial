"""
Formulários do sistema, com validações que aplicam as regras de negócio.
"""
import re

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.forms import BaseInlineFormSet, inlineformset_factory

from .models import EPI, Colaborador, Emprestimo, ItemEmprestimo, Usuario


def _aplicar_estilo(form):
    """Aplica a classe CSS padrão a todos os campos (consistência visual)."""
    for campo in form.fields.values():
        base = campo.widget.attrs.get('class', '')
        campo.widget.attrs['class'] = (base + ' campo').strip()


class ColaboradorForm(forms.ModelForm):
    class Meta:
        model = Colaborador
        fields = ['matricula', 'nome', 'cpf', 'data_nascimento',
                  'cargo', 'setor', 'telefone', 'email', 'ativo']
        widgets = {
            'data_nascimento': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_estilo(self)
        self.fields['cpf'].widget.attrs['placeholder'] = '000.000.000-00'

    def clean_cpf(self):
        """Normaliza e valida o CPF (11 dígitos)."""
        cpf = re.sub(r'\D', '', self.cleaned_data['cpf'])
        if len(cpf) != 11:
            raise forms.ValidationError('O CPF deve conter 11 dígitos.')
        return f'{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}'


class EPIForm(forms.ModelForm):
    class Meta:
        model = EPI
        fields = ['nome', 'descricao', 'categoria', 'ca_numero', 'ca_validade',
                  'tamanho', 'qtd_estoque', 'qtd_minima', 'ativo']
        widgets = {
            'ca_validade': forms.DateInput(attrs={'type': 'date'}, format='%Y-%m-%d'),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_estilo(self)


class UsuarioForm(UserCreationForm):
    class Meta:
        model = Usuario
        fields = ['first_name', 'last_name', 'username', 'email', 'perfil']
        labels = {'first_name': 'Nome', 'last_name': 'Sobrenome',
                  'username': 'Usuário (login)'}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        _aplicar_estilo(self)


class EmprestimoForm(forms.ModelForm):
    class Meta:
        model = Emprestimo
        fields = ['colaborador', 'data_prevista_devolucao', 'observacao']
        widgets = {
            'data_prevista_devolucao': forms.DateInput(attrs={'type': 'date'}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Só colaboradores ativos podem receber EPIs (RN01)
        self.fields['colaborador'].queryset = Colaborador.objects.filter(ativo=True)
        _aplicar_estilo(self)


class ItemEmprestimoForm(forms.ModelForm):
    class Meta:
        model = ItemEmprestimo
        fields = ['epi', 'quantidade']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Exibe apenas EPIs ativos; disponibilidade é validada no clean (RN02)
        self.fields['epi'].queryset = EPI.objects.filter(ativo=True)
        self.fields['epi'].label_from_instance = (
            lambda epi: f'{epi} | estoque: {epi.qtd_estoque}'
        )
        # Linhas extras podem ficar vazias — a validação de "pelo menos um
        # item" é feita no formset (BaseItemFormSet)
        self.fields['epi'].required = False
        self.fields['quantidade'].required = False
        _aplicar_estilo(self)

    def clean(self):
        """RN02: bloqueia EPI sem estoque suficiente ou com CA vencido (RF07)."""
        dados = super().clean()
        epi = dados.get('epi')
        qtd = dados.get('quantidade')
        if not epi and not qtd:
            return dados  # linha vazia — ignorada
        if qtd and not epi:
            raise forms.ValidationError('Selecione o EPI desta linha.')
        if epi and not qtd:
            dados['quantidade'] = 1  # padrão: 1 unidade
            qtd = 1
        if epi and qtd:
            if epi.ca_vencido:
                raise forms.ValidationError(
                    f'O CA do EPI "{epi.nome}" está vencido ({epi.ca_validade:%d/%m/%Y}). '
                    'Empréstimo bloqueado pela NR-6.')
            if qtd > epi.qtd_estoque:
                raise forms.ValidationError(
                    f'Estoque insuficiente para "{epi.nome}": '
                    f'disponível {epi.qtd_estoque}, solicitado {qtd}.')
        return dados


class BaseItemFormSet(BaseInlineFormSet):
    """Valida o conjunto de itens do empréstimo."""

    def clean(self):
        super().clean()
        if any(self.errors):
            return
        epis = []
        for form in self.forms:
            if form.cleaned_data and not form.cleaned_data.get('DELETE'):
                epi = form.cleaned_data.get('epi')
                if epi:
                    if epi in epis:
                        raise forms.ValidationError(
                            f'O EPI "{epi.nome}" foi adicionado mais de uma vez. '
                            'Some as quantidades em uma única linha.')
                    epis.append(epi)
        if not epis:
            raise forms.ValidationError('Adicione pelo menos um EPI ao empréstimo.')

    def save_new_objects(self, commit=True):
        """Salva apenas as linhas que possuem EPI selecionado."""
        self.new_objects = []
        for form in self.extra_forms:
            if not form.has_changed():
                continue
            if not form.cleaned_data.get('epi'):
                continue
            self.new_objects.append(self.save_new(form, commit=commit))
        return self.new_objects


ItemEmprestimoFormSet = inlineformset_factory(
    Emprestimo, ItemEmprestimo,
    form=ItemEmprestimoForm, formset=BaseItemFormSet,
    extra=3, can_delete=False,
)
