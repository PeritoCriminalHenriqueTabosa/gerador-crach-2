import os
from flask import Flask, render_template, request, send_file, redirect, url_for, flash
from PIL import Image, ImageDraw, ImageFont
import uuid # Para gerar nomes de arquivo únicos
import io # Para manipulação de streams de bytes

app = Flask(__name__)
app.secret_key = 'supersecretkey' # Chave secreta para mensagens flash
app.config['UPLOAD_FOLDER'] = 'uploads' # Pasta para uploads temporários
app.config['ALLOWED_EXTENSIONS'] = {'png', 'jpg', 'jpeg'} # Extensões permitidas
app.config['MAX_CONTENT_LENGTH'] = 2 * 1024 * 1024 # Limite de 2MB por arquivo

# Cria a pasta de uploads se ela não existir
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

# --- Configurações do Crachá ---
# Caminho para o template do crachá (assumindo que está em static/)
BADGE_TEMPLATE_PATH = os.path.join(app.root_path, 'static', 'template_cracha.png')
# Coordenadas da foto no template (x, y, largura, altura) - AJUSTE ESTES VALORES
# (330, 955, 370, 499) são suas coordenadas atuais
PHOTO_POSITION = (330, 955, 370, 499) 
# Coordenadas e tamanho da fonte para o nome (x, y do canto superior esquerdo do texto) - AJUSTE ESTES VALORES
# O valor X (0 neste exemplo) será ignorado para centralização horizontal.
# O valor Y (1540 neste exemplo) define a altura vertical do nome.
NAME_POSITION = (0, 1540) 
FONT_SIZE = 50
# Caminho para a fonte (assumindo que está em static/) - BAIXE UMA FONTE .ttf (ex: Roboto)
# Garanta que o arquivo 'Montserrat-Bold.ttf' esteja na pasta 'static'
FONT_PATH = os.path.join(app.root_path, 'static', 'Montserrat-Bold.ttf')

# --- Funções de Ajuda ---
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in app.config['ALLOWED_EXTENSIONS']

def process_badge(photo_file_stream, user_name):
    try:
        # Carrega o template do crachá
        # 'badge' é a variável que representa o template carregado
        badge = Image.open(BADGE_TEMPLATE_PATH).convert("RGBA")

        # Carrega a foto do usuário e a redimensiona
        user_photo = Image.open(photo_file_stream).convert("RGBA")
        photo_x, photo_y, photo_width, photo_height = PHOTO_POSITION
        user_photo = user_photo.resize((photo_width, photo_height), Image.Resampling.LANCZOS)

        # Cola a foto no crachá
        badge.paste(user_photo, (photo_x, photo_y), user_photo)

        # Prepara para desenhar texto
        # 'draw' é a variável que permite desenhar sobre a imagem 'badge'
        draw = ImageDraw.Draw(badge)
        try:
            # Tenta carregar a fonte personalizada
            font = ImageFont.truetype(FONT_PATH, FONT_SIZE)
        except IOError:
            # Se a fonte não for encontrada, usa a fonte padrão do Pillow
            print(f"ATENÇÃO: Fonte '{FONT_PATH}' não encontrada. Usando fonte padrão.")
            font = ImageFont.load_default()

        # --- Lógica para centralizar o nome horizontalmente ---
        # Pegamos a coordenada Y definida em NAME_POSITION (verticalmente fixa)
        # A coordenada X será calculada para centralizar o texto.
        _, name_y = NAME_POSITION # Ignora o X de NAME_POSITION, pega apenas o Y

        # 1. Obtém as dimensões (bounding box) do texto que será desenhado
        # O text_bbox retorna uma tupla (left, top, right, bottom) do retângulo que o texto ocupa
        text_bbox = draw.textbbox((0, 0), user_name, font=font)
        text_width = text_bbox[2] - text_bbox[0] # Calcula a largura real do texto

        # 2. Obtém a largura total do crachá
        badge_width, _ = badge.size # Pega a largura do crachá, ignorando a altura

        # 3. Calcula a nova coordenada X para centralizar o texto
        # Fórmula: (Largura total do crachá - Largura do texto) / 2
        name_x_centered = (badge_width - text_width) / 2

        # 4. Desenha o texto do nome na posição centralizada (X) e na altura definida (Y)
        draw.text((name_x_centered, name_y), user_name, font=font, fill=(0, 0, 0, 255)) # Cor preta (RGBA)
        # --- FIM da Lógica de centralização ---

        # Retorna o crachá processado como um stream de bytes
        img_byte_arr = io.BytesIO()
        badge.save(img_byte_arr, format='PNG')
        img_byte_arr.seek(0)
        return img_byte_arr

    except Exception as e:
        print(f"Erro ao processar o crachá: {e}")
        return None

# --- Rotas da Aplicação ---
@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        # 1. Validação do Upload da Foto
        if 'photo' not in request.files:
            flash('Nenhum arquivo de foto enviado.', 'error')
            return redirect(request.url)
        
        photo = request.files['photo']
        user_name = request.form.get('name', 'Nome do Participante')

        if photo.filename == '':
            flash('Nenhum arquivo de foto selecionado.', 'error')
            return redirect(request.url)
        
        if not allowed_file(photo.filename):
            flash('Formato de arquivo não permitido. Use PNG, JPG ou JPEG.', 'error')
            return redirect(request.url)
        
        # 2. Processamento do Crachá
        # O stream da foto é passado diretamente para evitar salvar no disco desnecessariamente.
        badge_stream = process_badge(photo.stream, user_name)

        if badge_stream:
            # 3. Enviar o arquivo para download
            # Use um nome de arquivo único para o crachá gerado
            generated_filename = f"cracha_{uuid.uuid4().hex}.png"
            return send_file(badge_stream, mimetype='image/png', as_attachment=True, download_name=generated_filename)
        else:
            flash('Erro ao gerar o crachá. Tente novamente.', 'error')
            return redirect(request.url)

    # Para requisições GET, renderiza o formulário
    return render_template('index.html')

if __name__ == '__main__':
    # Para rodar em ambiente de desenvolvimento, ative o modo debug
    app.run(debug=True)