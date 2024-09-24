from app import app
from flask import Flask, render_template, request, redirect, url_for, flash, session
import requests
from getpass import getpass
from flask import send_file
from reportlab.lib.pagesizes import letter
from reportlab.pdfgen import canvas
import io
import requests

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
            
            return render_template('dashboard.html', dados=meus_dados, vinculo=meus_dados['vinculo'])
        else:
            flash("Credenciais inválidas. Tente novamente.")
            return render_template('index.html')
    else:
        return render_template('index.html')


@app.route('/dashboard', methods=['GET', 'POST'])    
def dashboard():
    if request.method == 'GET':
        return render_template('dashboard.html')
    else:
        return render_template('dashboard.html')





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
    token = session.get('token')  # Recupera o token da sessão
    if not token:
        flash('Usuário não autenticado. Faça login novamente.')
        return redirect(url_for('index'))

    headers = {"Authorization": f'Bearer {token}'}

    # Busca os dados pessoais do aluno
    dados_response = requests.get(f"{api_url}v2/minhas-informacoes/meus-dados/", headers=headers)
    if dados_response.status_code != 200:
        flash("Erro ao buscar dados do aluno.")
        return redirect(url_for('index'))

    dados_aluno = dados_response.json()

    # Busca os períodos letivos do aluno
    periodos_response = requests.get(f"{api_url}v2/minhas-informacoes/meus-periodos-letivos/", headers=headers)
    if periodos_response.status_code != 200:
        flash("Erro ao buscar períodos letivos.")
        return redirect(url_for('index'))

    periodos = periodos_response.json()

    # Criar o buffer para o PDF
    buffer = io.BytesIO()
    pdf = canvas.Canvas(buffer, pagesize=letter)
    pdf.setTitle("Dados Pessoais e Boletim")

    # Adiciona os dados pessoais ao PDF
    pdf.drawString(100, 750, f"Nome: {dados_aluno['nome_usual']}")
    pdf.drawString(100, 735, f"Matrícula: {dados_aluno['matricula']}")
    pdf.drawString(100, 720, f"Email: {dados_aluno['email']}")
    pdf.drawString(100, 705, f"CPF: {dados_aluno['cpf']}")
    pdf.drawString(100, 690, f"Data de Nascimento: {dados_aluno['data_nascimento']}")
    pdf.drawString(100, 675, f"Curso: {dados_aluno['vinculo']['curso']}")

    # Adiciona os boletins ao PDF
    y_position = 650
    pdf.drawString(100, y_position, "Boletim:")
    y_position -= 15

    for periodo in periodos:
        ano_letivo = periodo['ano_letivo']
        periodo_letivo = periodo['periodo_letivo']
        boletim_response = requests.get(f"{api_url}v2/minhas-informacoes/boletim/{ano_letivo}/{periodo_letivo}/", headers=headers)
        
        if boletim_response.status_code == 200:
            boletim_data = boletim_response.json()
            pdf.drawString(100, y_position, f"Ano: {ano_letivo}, Período: {periodo_letivo}")
            y_position -= 10
            
            for disciplina in boletim_data:
                pdf.drawString(120, y_position, f"{disciplina['disciplina']}: {disciplina['media_final_disciplina']}")
                y_position -= 10
        else:
            pdf.drawString(100, y_position, f"Erro ao buscar boletim para {ano_letivo}/{periodo_letivo}")
            y_position -= 10

    pdf.save()
    buffer.seek(0)

    
    return send_file(buffer, as_attachment=True, download_name='dados_pessoais_boletim.pdf')

