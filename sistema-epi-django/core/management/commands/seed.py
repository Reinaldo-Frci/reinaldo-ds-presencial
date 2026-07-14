from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from core.models import EPI, Colaborador, Emprestimo, ItemEmprestimo, Usuario


class Command(BaseCommand):
    help = 'Cria usuários, colaboradores, EPIs e empréstimos de demonstração.'

    def handle(self, *args, **options):
        if Usuario.objects.exists():
            self.stdout.write(self.style.WARNING('Banco já possui dados — seed ignorado.'))
            return

        hoje = timezone.localdate()

        Usuario.objects.create_superuser(
            username='admin', password='admin123', email='admin@construtora.com.br',
            first_name='Administrador', perfil=Usuario.Perfil.ADMINISTRADOR)
        tecnico = Usuario.objects.create_user(
            username='tecnico', password='tecnico123', email='tecnico@construtora.com.br',
            first_name='Ana', last_name='Lima', perfil=Usuario.Perfil.TECNICO)
        Usuario.objects.create_user(
            username='almoxarife', password='almoxarife123',
            first_name='Paulo', last_name='Souza', perfil=Usuario.Perfil.ALMOXARIFE)

        colaboradores = [
            ('001201', 'Carlos Andrade', '111.444.777-35', 'Pedreiro', 'Estrutura'),
            ('001202', 'José Pereira', '222.555.888-46', 'Servente', 'Alvenaria'),
            ('001203', 'Marcos Oliveira', '333.666.999-57', 'Eletricista', 'Elétrica'),
            ('001204', 'Fernanda Costa', '444.777.111-68', 'Mestre de obras', 'Estrutura'),
            ('001205', 'Ricardo Santos', '555.888.222-79', 'Pintor', 'Acabamento'),
        ]
        Colaborador.objects.bulk_create([
            Colaborador(matricula=m, nome=n, cpf=c, cargo=cg, setor=s)
            for m, n, c, cg, s in colaboradores])

        epis = [
            ('Capacete de segurança com jugular', EPI.Categoria.CABECA,
             'CA 12345', hoje + timedelta(days=400), 'Único', 90, 15),
            ('Botina de segurança com biqueira', EPI.Categoria.PES,
             'CA 23456', hoje + timedelta(days=200), '42', 60, 10),
            ('Cinto de segurança tipo paraquedista', EPI.Categoria.ALTURA,
             'CA 34567', hoje + timedelta(days=25), 'Único', 6, 5),
            ('Luva de vaqueta', EPI.Categoria.MAOS,
             'CA 45678', hoje + timedelta(days=300), 'M', 120, 20),
            ('Óculos de proteção incolor', EPI.Categoria.VISUAL,
             'CA 56789', hoje + timedelta(days=500), 'Único', 80, 10),
            ('Protetor auricular plug', EPI.Categoria.AUDITIVA,
             'CA 67890', hoje - timedelta(days=10), 'Único', 200, 50),
        ]
        for nome, cat, ca, val, tam, est, minimo in epis:
            EPI.objects.create(nome=nome, categoria=cat, ca_numero=ca,
                               ca_validade=val, tamanho=tam,
                               qtd_estoque=est, qtd_minima=minimo)

        carlos = Colaborador.objects.get(matricula='001201')
        jose = Colaborador.objects.get(matricula='001202')
        capacete = EPI.objects.get(ca_numero='CA 12345')
        botina = EPI.objects.get(ca_numero='CA 23456')

        emp1 = Emprestimo.objects.create(
            colaborador=carlos, usuario=tecnico,
            data_prevista_devolucao=hoje + timedelta(days=15))
        ItemEmprestimo.objects.create(emprestimo=emp1, epi=capacete, quantidade=1)
        ItemEmprestimo.objects.create(emprestimo=emp1, epi=botina, quantidade=1)
        capacete.qtd_estoque -= 1
        capacete.save()
        botina.qtd_estoque -= 1
        botina.save()

        emp2 = Emprestimo.objects.create(
            colaborador=jose, usuario=tecnico,
            data_prevista_devolucao=hoje - timedelta(days=3))
        ItemEmprestimo.objects.create(emprestimo=emp2, epi=capacete, quantidade=1)
        capacete.qtd_estoque -= 1
        capacete.save()

        self.stdout.write(self.style.SUCCESS(
            'Dados de demonstração criados.\n'
            'Logins: admin/admin123 (Administrador) · tecnico/tecnico123 (Técnico) · '
            'almoxarife/almoxarife123 (Almoxarife)'))
