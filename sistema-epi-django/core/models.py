from datetime import timedelta

from django.contrib.auth.models import AbstractUser
from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Usuario(AbstractUser):

    class Perfil(models.TextChoices):
        ADMINISTRADOR = 'ADMINISTRADOR', 'Administrador'
        TECNICO = 'TECNICO', 'Técnico de Segurança'
        ALMOXARIFE = 'ALMOXARIFE', 'Almoxarife'

    perfil = models.CharField('Perfil de acesso', max_length=20,
                              choices=Perfil.choices, default=Perfil.TECNICO)

    @property
    def eh_admin(self):
        return self.perfil == self.Perfil.ADMINISTRADOR or self.is_superuser

    def __str__(self):
        return self.get_full_name() or self.username


class Colaborador(models.Model):
    matricula = models.CharField('Matrícula', max_length=20, unique=True)
    nome = models.CharField('Nome completo', max_length=100)
    cpf = models.CharField('CPF', max_length=14, unique=True,
                           help_text='Somente números ou no formato 000.000.000-00')
    data_nascimento = models.DateField('Data de nascimento', null=True, blank=True)
    cargo = models.CharField('Cargo', max_length=60)
    setor = models.CharField('Setor', max_length=60)
    telefone = models.CharField('Telefone', max_length=15, blank=True)
    email = models.EmailField('E-mail', blank=True)
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'colaborador'
        verbose_name_plural = 'colaboradores'

    def __str__(self):
        return f'{self.matricula} — {self.nome}'


class EPI(models.Model):

    class Categoria(models.TextChoices):
        CABECA = 'CABECA', 'Proteção da cabeça'
        AUDITIVA = 'AUDITIVA', 'Proteção auditiva'
        RESPIRATORIA = 'RESPIRATORIA', 'Proteção respiratória'
        VISUAL = 'VISUAL', 'Proteção visual'
        MAOS = 'MAOS', 'Proteção das mãos'
        PES = 'PES', 'Proteção dos pés'
        TRONCO = 'TRONCO', 'Proteção do tronco'
        ALTURA = 'ALTURA', 'Trabalho em altura'
        OUTROS = 'OUTROS', 'Outros'

    nome = models.CharField('Nome do EPI', max_length=100)
    descricao = models.CharField('Descrição', max_length=255, blank=True)
    categoria = models.CharField('Categoria', max_length=20, choices=Categoria.choices)
    ca_numero = models.CharField('Nº do CA', max_length=20,
                                 help_text='Certificado de Aprovação (NR-6)')
    ca_validade = models.DateField('Validade do CA')
    tamanho = models.CharField('Tamanho', max_length=10, blank=True)
    qtd_estoque = models.PositiveIntegerField('Qtde. em estoque', default=0)
    qtd_minima = models.PositiveIntegerField('Estoque mínimo', default=5)
    ativo = models.BooleanField('Ativo', default=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nome']
        verbose_name = 'EPI'
        verbose_name_plural = 'EPIs'

    @property
    def ca_vencido(self):
        return self.ca_validade < timezone.localdate()

    @property
    def ca_a_vencer(self):
        hoje = timezone.localdate()
        return not self.ca_vencido and self.ca_validade <= hoje + timedelta(days=30)

    @property
    def estoque_baixo(self):
        return self.qtd_estoque <= self.qtd_minima

    @property
    def disponivel(self):
        return self.ativo and self.qtd_estoque > 0 and not self.ca_vencido

    def __str__(self):
        extra = f' ({self.tamanho})' if self.tamanho else ''
        return f'{self.nome}{extra} — {self.ca_numero}'


class Emprestimo(models.Model):

    class Status(models.TextChoices):
        ATIVO = 'ATIVO', 'Ativo'
        DEVOLVIDO = 'DEVOLVIDO', 'Devolvido'
        ATRASADO = 'ATRASADO', 'Atrasado'

    colaborador = models.ForeignKey(Colaborador, on_delete=models.PROTECT,
                                    related_name='emprestimos', verbose_name='Colaborador')
    usuario = models.ForeignKey('core.Usuario', on_delete=models.PROTECT,
                                related_name='emprestimos_registrados',
                                verbose_name='Registrado por')
    data_emprestimo = models.DateTimeField('Data do empréstimo', auto_now_add=True)
    data_prevista_devolucao = models.DateField('Data prevista de devolução')
    status = models.CharField('Status', max_length=10,
                              choices=Status.choices, default=Status.ATIVO)
    observacao = models.CharField('Observação', max_length=255, blank=True)

    class Meta:
        ordering = ['-data_emprestimo']
        verbose_name = 'empréstimo'
        verbose_name_plural = 'empréstimos'

    @classmethod
    def atualizar_atrasados(cls):
        cls.objects.filter(
            status=cls.Status.ATIVO,
            data_prevista_devolucao__lt=timezone.localdate(),
        ).update(status=cls.Status.ATRASADO)

    @property
    def itens_pendentes(self):
        return self.itens.filter(data_devolucao__isnull=True)

    def __str__(self):
        return f'Empréstimo nº {self.pk} — {self.colaborador.nome}'


class ItemEmprestimo(models.Model):

    class Condicao(models.TextChoices):
        BOM_ESTADO = 'BOM_ESTADO', 'Bom estado'
        DANIFICADO = 'DANIFICADO', 'Danificado'
        EXTRAVIADO = 'EXTRAVIADO', 'Extraviado'

    emprestimo = models.ForeignKey(Emprestimo, on_delete=models.CASCADE,
                                   related_name='itens')
    epi = models.ForeignKey(EPI, on_delete=models.PROTECT,
                            related_name='itens_emprestados', verbose_name='EPI')
    quantidade = models.PositiveIntegerField('Quantidade', default=1,
                                             validators=[MinValueValidator(1)])
    data_devolucao = models.DateTimeField('Data da devolução', null=True, blank=True)
    condicao_devolucao = models.CharField('Condição na devolução', max_length=12,
                                          choices=Condicao.choices, blank=True)

    class Meta:
        verbose_name = 'item do empréstimo'
        verbose_name_plural = 'itens do empréstimo'

    @property
    def devolvido(self):
        return self.data_devolucao is not None

    def __str__(self):
        return f'{self.quantidade}x {self.epi.nome}'
