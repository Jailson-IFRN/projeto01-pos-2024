from app import app
from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from getpass import getpass
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import requests
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from reportlab.platypus import Table, TableStyle, SimpleDocTemplate



api_url = "https://suap.ifrn.edu.br/api/"





@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        user = request.form['matricula']
        password = request.form['password']
        data = {"username": user, "password": password}
        response = requests.post(api_url + "v2/autenticacao/token/", json=data)

        if response.status_code == 200:
            token = response.json()["access"]
            session['token'] = token  # Vou tentar armazenar aqui o token na sessão
            headers = {"Authorization": f'Bearer {token}'}
            response = requests.get(f"{api_url}v2/minhas-informacoes/meus-dados/", headers=headers)
            meus_dados = response.json()
            print(meus_dados['nome_usual'])
            return render_template('dashboard.html', dados=meus_dados, vinculo=meus_dados['vinculo'])
        else:
            flash("Credenciais inválidas. Tente novamente.")
            return render_template('index.html')
    else:
        return render_template('index.html')


@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    
    token = session.get('token')
    
    if not token:
        flash("Você precisa estar logado para acessar o dashboard.")
        return redirect(url_for('index'))

    headers = {"Authorization": f'Bearer {token}'}
    response = requests.get(f"{api_url}v2/minhas-informacoes/meus-dados/", headers=headers)
    
    if response.status_code == 200:
        meus_dados = response.json()
        return render_template('dashboard.html', dados=meus_dados, vinculo=meus_dados['vinculo'])
    else:
        flash("Erro ao carregar os dados do usuário.")
        return redirect(url_for('index'))






@app.route('/meu/boletim/suap', methods=['GET', 'POST'])
def boletim():
    token = session.get('token')  # Recupera o token da sessão lá de cim
    if not token:
        flash('Usuário não autenticado. Faça login novamente.')
        return redirect(url_for('index'))

    headers = {"Authorization": f'Bearer {token}'}

    if request.method == 'POST':
        ano_letivo = request.form['ano_letivo']
        periodo_letivo = request.form['periodo_letivo']

        # Busca os dados do boletim para o ano e período letivo
        boletim_response = requests.get(f"{api_url}v2/minhas-informacoes/boletim/{ano_letivo}/{periodo_letivo}/", headers=headers)

        if boletim_response.status_code == 200:
            boletim_data = boletim_response.json()
            return render_template('meu_boletim.html', boletim=boletim_data)
        else:
            flash("Erro ao buscar o boletim.")
            return render_template('meu_boletim.html')
    
    return render_template('meu_boletim.html')




@app.route('/meus/dados/pessoais')
def students():
    token = session.get('token')  # Recupera o token da sessão
    if not token:
        flash('Usuário não autenticado. Faça login novamente.')
        return redirect(url_for('index'))

    headers = {"Authorization": f'Bearer {token}'}
    response = requests.get(f"{api_url}v2/minhas-informacoes/meus-dados/", headers=headers)

    if response.status_code == 200:
        dados_aluno = response.json()
        return render_template('dados_pessoais.html', dados=dados_aluno, vinculo=dados_aluno['vinculo'])
    else:
        flash("Erro ao buscar dados do aluno.")
        return redirect(url_for('index'))





@app.route('/gerar_pdf')
def gerar_pdf():
    token = session.get('token')  
    if not token:
        flash('Usuário não autenticado. Faça login novamente.')
        return redirect(url_for('index'))

    headers = {"Authorization": f'Bearer {token}'}


    dados_response = requests.get(f"{api_url}v2/minhas-informacoes/meus-dados/", headers=headers)
    if dados_response.status_code != 200:
        flash("Erro ao buscar dados do aluno.")
        return redirect(url_for('index'))

    dados_aluno = dados_response.json()


    periodos_response = requests.get(f"{api_url}v2/minhas-informacoes/meus-periodos-letivos/", headers=headers)
    if periodos_response.status_code != 200:
        flash("Erro ao buscar períodos letivos.")
        return redirect(url_for('index'))

    periodos = periodos_response.json()

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter)
    elements = []

    # data
    dados_pessoais = [
        ['Nome:', dados_aluno['nome_usual']],
        ['Matrícula:', dados_aluno['matricula']],
        ['Email:', dados_aluno['email']],
        ['CPF:', dados_aluno['cpf']],
        ['Data de Nascimento:', dados_aluno['data_nascimento']],
        ['Curso:', dados_aluno['vinculo']['curso']]
    ]

    tabela_dados = Table(dados_pessoais, colWidths=[2 * inch, 4 * inch])
    tabela_dados.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))
    elements.append(tabela_dados)

    
    for periodo in periodos:
        ano_letivo = periodo['ano_letivo']
        periodo_letivo = periodo['periodo_letivo']
        boletim_response = requests.get(f"{api_url}v2/minhas-informacoes/boletim/{ano_letivo}/{periodo_letivo}/", headers=headers)

        if boletim_response.status_code == 200:
            boletim_data = boletim_response.json()
            
        
            elements.append(Table([[f"Ano: {ano_letivo} - Período: {periodo_letivo}"]], colWidths=[6 * inch]))
            
    
            boletim_table_data = [['Disciplina', 'Média Final']]
            for disciplina in boletim_data:
                boletim_table_data.append([disciplina['disciplina'], disciplina['media_final_disciplina']])
            
            boletim_table = Table(boletim_table_data, colWidths=[4 * inch, 2 * inch])
            boletim_table.setStyle(TableStyle([
                ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                ('FONTSIZE', (0, 0), (-1, -1), 10),
                ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
                ('GRID', (0, 0), (-1, -1), 1, colors.black),
            ]))
            elements.append(boletim_table)
        else:
            elements.append(Table([[f"Erro ao buscar boletim para {ano_letivo}/{periodo_letivo}"]], colWidths=[6 * inch]))

    doc.build(elements)
    buffer.seek(0)

    return send_file(buffer, as_attachment=True, download_name='dados_pessoais_boletim.pdf')


