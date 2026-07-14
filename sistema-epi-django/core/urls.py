from django.urls import path

from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    # Colaboradores (RF01)
    path('colaboradores/', views.colaborador_lista, name='colaborador_lista'),
    path('colaboradores/novo/', views.colaborador_form, name='colaborador_novo'),
    path('colaboradores/<int:pk>/editar/', views.colaborador_form, name='colaborador_editar'),
    path('colaboradores/<int:pk>/toggle/', views.colaborador_toggle, name='colaborador_toggle'),
    # EPIs (RF02)
    path('epis/', views.epi_lista, name='epi_lista'),
    path('epis/novo/', views.epi_form, name='epi_novo'),
    path('epis/<int:pk>/editar/', views.epi_form, name='epi_editar'),
    path('epis/<int:pk>/toggle/', views.epi_toggle, name='epi_toggle'),
    # Empréstimos (RF05/RF06/RF10)
    path('emprestimos/', views.emprestimo_lista, name='emprestimo_lista'),
    path('emprestimos/novo/', views.emprestimo_novo, name='emprestimo_novo'),
    path('emprestimos/<int:pk>/devolucao/', views.emprestimo_devolucao, name='emprestimo_devolucao'),
    path('emprestimos/<int:pk>/ficha/', views.emprestimo_ficha, name='emprestimo_ficha'),
    # Usuários (RF03)
    path('usuarios/', views.usuario_lista, name='usuario_lista'),
    path('usuarios/novo/', views.usuario_novo, name='usuario_novo'),
    # Relatórios (RF09 — bônus)
    path('relatorios/', views.relatorios, name='relatorios'),
]
