# Sistema de Gerenciamento de EPIs — Construção Civil

Sistema web para controle de empréstimo de Equipamentos de Proteção Individual (EPIs)
aos colaboradores de uma empresa de construção civil, em conformidade com a **NR-6**.

Projeto da Situação de Aprendizagem — 4ª fase, CT Desenvolvimento de Sistemas.

## Funcionalidades

| Funcionalidade | Critério da S.A. | Onde está |
|---|---|---|
| Cadastro de colaboradores (busca, filtro por setor, inativação lógica) | Crítico | Menu **Colaboradores** |
| Cadastro de EPIs com nº do CA, validade e estoque | Crítico | Menu **EPIs** |
| Empréstimo de EPIs associado a colaboradores, com validação de estoque e CA | Crítico | Menu **Empréstimos → Registrar** |
| Devolução com condição do item (bom estado retorna ao estoque) | Crítico | Menu **Empréstimos → Devolução** |
| Controle de estoque (baixa/retorno automáticos + alertas de mínimo) | Desejável | Automático + **Dashboard** |
| Cadastro de usuários com perfis (Administrador, Técnico, Almoxarife) | Desejável | Menu **Usuários** (perfil Administrador) |
| Relatórios por colaborador e por equipamento | Bônus | Menu **Relatórios** |
| Ficha de entrega de EPI para impressão (registro NR-6) | — | Botão **Ficha** em cada empréstimo |

## Regras de negócio implementadas

- **RN02/RF07**: empréstimo bloqueado se não houver estoque ou se o CA estiver vencido;
- **RN03**: devolução em bom estado retorna ao estoque; danificado/extraviado não retorna;
- **RN04**: empréstimos com prazo vencido mudam automaticamente para **Atrasado**;
- **RN05**: colaboradores e EPIs são inativados (não excluídos), preservando o histórico.

## Como executar

Pré-requisito: Python 3.10+

```bash
# 1. Criar e ativar o ambiente virtual
python -m venv venv
venv\Scripts\activate        # Windows
source venv/bin/activate     # Linux/Mac

# 2. Instalar as dependências
pip install -r requirements.txt

# 3. Criar o banco de dados (SQLite, zero configuração)
python manage.py migrate

# 4. Popular com dados de demonstração
python manage.py seed

# 5. Iniciar o servidor
python manage.py runserver
```

Acesse **http://127.0.0.1:8000** e entre com um dos usuários:

| Usuário | Senha | Perfil |
|---|---|---|
| `admin` | `admin123` | Administrador (acessa tudo, inclusive Usuários) |
| `tecnico` | `tecnico123` | Técnico de Segurança |
| `almoxarife` | `almoxarife123` | Almoxarife |

Os dados de demonstração incluem um EPI com **CA vencido** (protetor auricular) e um
empréstimo **atrasado**, para demonstrar as validações e alertas na apresentação.

## Estrutura do projeto

```
sistema-epi-django/
├── manage.py
├── requirements.txt
├── sistema_epi/          # configurações do projeto
├── core/                 # app principal
│   ├── models.py         # Usuario, Colaborador, EPI, Emprestimo, ItemEmprestimo (DER)
│   ├── forms.py          # validações das regras de negócio
│   ├── views.py          # telas e fluxos (cada view referencia o RF que atende)
│   └── management/commands/seed.py
├── templates/core/       # telas do sistema
└── static/css/style.css  # identidade visual
```

## Documentação (Etapa 1)

A documentação técnica completa (requisitos, DER, casos de uso e wireframes)
acompanha o projeto na pasta `docs/`.
