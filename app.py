from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-super-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gimnasio.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# MODELO DE USUARIO (Con roles: admin, profesor, alumno)
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    rol = db.Column(db.String(20), nullable=False) # 'admin', 'profesor', 'alumno'
    plan = db.Column(db.String(50), default='Ninguno')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Crear la base de datos y un usuario Administrador por defecto al iniciar
with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(username='admin').first():
        admin_user = Usuario(
            username='admin',
            password=generate_password_hash('admin123', method='pbkdf2:sha256'),
            nombre='Administrador',
            apellido='General',
            rol='admin'
        )
        db.session.add(admin_user)
        db.session.commit()

# RUTAS DE AUTENTICACIÓN
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.rol == 'admin':
            return redirect(url_for('admin_panel'))
        elif current_user.rol == 'profesor':
            return redirect(url_for('profesor_panel'))
        else:
            return redirect(url_for('alumno_panel'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = Usuario.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for('index'))
        flash('Usuario o contraseña incorrectos', 'danger')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        nombre = request.form['nombre']
        apellido = request.form['apellido']
        plan = request.form['plan']

        # Verificar si el usuario ya existe
        usuario_existente = Usuario.query.filter_by(username=username).first()
        if usuario_existente:
            flash('El nombre de usuario ya está en uso. Elegí otro.', 'danger')
            return redirect(url_for('registro'))

        nuevo_usuario = Usuario(
            username=username,
            password=generate_password_hash(password, method='pbkdf2:sha256'),
            nombre=nombre,
            apellido=apellido,
            rol='alumno',
            plan=plan
        )
        db.session.add(nuevo_usuario)
        db.session.commit()
        flash('¡Cuenta creada con éxito! Ya podés iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# PANELES SEGÚN EL ROL
@app.route('/admin')
@login_required
def admin_panel():
    if current_user.rol != 'admin':
        return "Acceso denegado", 403
    usuarios = Usuario.query.all()
    return render_template('admin.html', usuarios=usuarios)

@app.route('/profesor')
@login_required
def profesor_panel():
    if current_user.rol != 'profesor':
        return "Acceso denegado", 403
    return render_template('profesor.html')

@app.route('/alumno')
@login_required
def alumno_panel():
    if current_user.rol != 'alumno':
        return "Acceso denegado", 403
    return render_template('alumno.html')

if __name__ == '__main__':
    app.run(debug=True)