from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-super-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gimnasio.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# TABLAS DE LA BASE DE DATOS
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    rol = db.Column(db.String(20), nullable=False) # 'admin', 'profesor', 'alumno'
    plan = db.Column(db.String(50), default='Ninguno')

class Disciplina(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nombre = db.Column(db.String(50), nullable=False)
    descripcion = db.Column(db.String(200))
    estado = db.Column(db.String(20), default='Activa')

class Clase(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    disciplina_id = db.Column(db.Integer, db.ForeignKey('disciplina.id'), nullable=False)
    fecha = db.Column(db.String(20), nullable=False)
    hora = db.Column(db.String(10), nullable=False)
    cupo = db.Column(db.Integer, nullable=False)
    
    disciplina = db.relationship('Disciplina', backref='clases')
    reservas = db.relationship('Reserva', backref='clase_reservada', lazy=True, cascade="all, delete-orphan")

class Reserva(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)
    clase_id = db.Column(db.Integer, db.ForeignKey('clase.id'), nullable=False)
    
    usuario = db.relationship('Usuario', backref='mis_reservas')

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# Crear base de datos al iniciar
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

        if Usuario.query.filter_by(username=username).first():
            flash('El usuario ya existe.', 'danger')
            return redirect(url_for('registro'))

        nuevo = Usuario(
            username=username, password=generate_password_hash(password, method='pbkdf2:sha256'),
            nombre=nombre, apellido=apellido, rol='alumno', plan=plan
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Cuenta creada. Ya podés iniciar sesión.', 'success')
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

# PANELES DE ADMIN
@app.route('/admin')
@login_required
def admin_panel():
    if current_user.rol != 'admin': return "Denegado", 403
    usuarios = Usuario.query.all()
    return render_template('admin.html', usuarios=usuarios)

@app.route('/admin/disciplinas', methods=['GET', 'POST'])
@login_required
def admin_disciplinas():
    if current_user.rol != 'admin': return "Denegado", 403
    if request.method == 'POST':
        db.session.add(Disciplina(nombre=request.form['nombre'], descripcion=request.form['descripcion']))
        db.session.commit()
        return redirect(url_for('admin_disciplinas'))
    return render_template('admin_disciplinas.html', disciplinas=Disciplina.query.all())

# NUEVO: RUTAS DE AGENDA CON GENERADOR
@app.route('/admin/clases', methods=['GET', 'POST'])
@login_required
def admin_clases():
    if current_user.rol != 'admin': return "Denegado", 403
    
    if request.method == 'POST':
        disciplina_id = request.form['disciplina_id']
        dia_semana = int(request.form['dia_semana']) # 0=Lunes, 6=Domingo
        hora = request.form['hora']
        cupo = request.form['cupo']
        meses = int(request.form['meses'])
        
        # Calcular cuantas semanas generar
        semanas = meses * 4
        fecha_actual = date.today()
        # Buscar el próximo día que coincida con el día de la semana elegido
        dias_faltantes = (dia_semana - fecha_actual.weekday()) % 7
        fecha_clase = fecha_actual + timedelta(days=dias_faltantes)
        
        clases_creadas = 0
        for i in range(semanas):
            fecha_str = fecha_clase.strftime('%Y-%m-%d')
            # Verifica si ya existe para no duplicar turnos en el mismo horario
            if not Clase.query.filter_by(disciplina_id=disciplina_id, fecha=fecha_str, hora=hora).first():
                db.session.add(Clase(disciplina_id=disciplina_id, fecha=fecha_str, hora=hora, cupo=cupo))
                clases_creadas += 1
            fecha_clase += timedelta(days=7) # Salta a la próxima semana
            
        db.session.commit()
        flash(f'Éxito: Se generaron {clases_creadas} clases fijas.', 'success')
        return redirect(url_for('admin_clases'))
        
    # Mostrar solo clases de hoy en adelante para no llenar la pantalla de historial
    hoy = date.today().strftime('%Y-%m-%d')
    clases = Clase.query.filter(Clase.fecha >= hoy).order_by(Clase.fecha, Clase.hora).all()
    disciplinas = Disciplina.query.all()
    return render_template('admin_clases.html', clases=clases, disciplinas=disciplinas)

@app.route('/admin/clases/eliminar/<int:clase_id>')
@login_required
def eliminar_clase(clase_id):
    if current_user.rol != 'admin': return "Denegado", 403
    clase = Clase.query.get_or_404(clase_id)
    db.session.delete(clase)
    db.session.commit()
    flash('Clase cancelada correctamente.', 'success')
    return redirect(url_for('admin_clases'))

@app.route('/admin/clases/<int:clase_id>/inscriptos')
@login_required
def admin_inscriptos(clase_id):
    if current_user.rol != 'admin': return "Denegado", 403
    return render_template('admin_inscriptos.html', clase=Clase.query.get_or_404(clase_id))

# PANELES DE PROFESOR Y ALUMNO
@app.route('/profesor')
@login_required
def profesor_panel():
    if current_user.rol != 'profesor': return "Denegado", 403
    return render_template('profesor.html')

@app.route('/alumno')
@login_required
def alumno_panel():
    if current_user.rol != 'alumno': return "Denegado", 403
    hoy = date.today().strftime('%Y-%m-%d')
    clases = Clase.query.filter(Clase.fecha >= hoy).order_by(Clase.fecha, Clase.hora).all()
    mis_reservas_ids = [reserva.clase_id for reserva in current_user.mis_reservas]
    return render_template('alumno.html', clases=clases, mis_reservas_ids=mis_reservas_ids)

@app.route('/reservar/<int:clase_id>', methods=['POST'])
@login_required
def reservar_clase(clase_id):
    if current_user.rol != 'alumno': return "Denegado", 403
    clase = Clase.query.get_or_404(clase_id)
    
    if Reserva.query.filter_by(usuario_id=current_user.id, clase_id=clase_id).first():
        flash('Ya estás anotado en esta clase.', 'danger')
    elif len(clase.reservas) >= clase.cupo:
        flash('La clase está llena.', 'danger')
    else:
        db.session.add(Reserva(usuario_id=current_user.id, clase_id=clase_id))
        db.session.commit()
        flash('¡Reservado con éxito!', 'success')
    return redirect(url_for('alumno_panel'))

if __name__ == '__main__':
    app.run(debug=True)