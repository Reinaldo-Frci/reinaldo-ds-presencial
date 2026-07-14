from django.contrib import admin
from django.contrib.auth.admin import UserAdmin

from .models import EPI, Colaborador, Emprestimo, ItemEmprestimo, Usuario


@admin.register(Usuario)
class UsuarioAdmin(UserAdmin):
    fieldsets = UserAdmin.fieldsets + (('Perfil', {'fields': ('perfil',)}),)
    list_display = ('username', 'first_name', 'email', 'perfil', 'is_active')


@admin.register(Colaborador)
class ColaboradorAdmin(admin.ModelAdmin):
    list_display = ('matricula', 'nome', 'setor', 'cargo', 'ativo')
    search_fields = ('nome', 'matricula', 'cpf')
    list_filter = ('setor', 'ativo')


@admin.register(EPI)
class EPIAdmin(admin.ModelAdmin):
    list_display = ('nome', 'categoria', 'ca_numero', 'ca_validade',
                    'qtd_estoque', 'qtd_minima', 'ativo')
    list_filter = ('categoria', 'ativo')
    search_fields = ('nome', 'ca_numero')


class ItemInline(admin.TabularInline):
    model = ItemEmprestimo
    extra = 0


@admin.register(Emprestimo)
class EmprestimoAdmin(admin.ModelAdmin):
    list_display = ('id', 'colaborador', 'data_emprestimo',
                    'data_prevista_devolucao', 'status')
    list_filter = ('status',)
    inlines = [ItemInline]
