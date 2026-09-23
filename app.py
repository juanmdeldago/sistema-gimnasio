from flask import Flask, render_template, redirect, url_for, request, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, date, timedelta

app = Flask(__name__)
app.config['SECRET_KEY'] = 'clave-secreta-super-segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///gimnasio.db'

db = SQLAlchemy(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'

# NUEVOS MODELOS (Con email, telefono, vencimiento y asignacion)
class Usuario(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    nombre = db.Column(db.String(50), nullable=False)
    apellido = db.Column(db.String(50), nullable=False)
    email = db.Column(db.String(100))
    telefono = db.Column(db.String(20))
    rol = db.Column(db.String(20), nullable=False)
    
    disciplina_asignada_id = db.Column(db.Integer, db.ForeignKey('disciplina.id'), nullable=True)
    vencimiento = db.Column(db.Date, nullable=True)
    
    disciplina_asignada = db.relationship('Disciplina')

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

with app.app_context():
    db.create_all()
    if not Usuario.query.filter_by(username='admin').first():
        db.session.add(Usuario(
            username='admin', password=generate_password_hash('admin123', method='pbkdf2:sha256'),
            nombre='Admin', apellido='General', rol='admin'
        ))
        db.session.commit()

@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.rol == 'admin': return redirect(url_for('admin_panel'))
        else: return redirect(url_for('alumno_panel'))
    return redirect(url_for('login'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        user = Usuario.query.filter_by(username=request.form['username']).first()
        if user and check_password_hash(user.password, request.form['password']):
            login_user(user)
            return redirect(url_for('index'))
        flash('Credenciales incorrectas', 'danger')
    return render_template('login.html')

@app.route('/registro', methods=['GET', 'POST'])
def registro():
    if request.method == 'POST':
        username = request.form['username']
        if Usuario.query.filter_by(username=username).first():
            flash('El usuario ya existe.', 'danger')
            return redirect(url_for('registro'))
        nuevo = Usuario(
            username=username, 
            password=generate_password_hash(request.form['password'], method='pbkdf2:sha256'),
            nombre=request.form['nombre'], 
            apellido=request.form['apellido'],
            email=request.form['email'],
            telefono=request.form['telefono'],
            rol='alumno'
        )
        db.session.add(nuevo)
        db.session.commit()
        flash('Cuenta creada. Esperá que el administrador te asigne una actividad.', 'success')
        return redirect(url_for('login'))
    return render_template('registro.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

def obtener_dias_semana_actual():
    hoy = date.today()
    inicio_semana = hoy - timedelta(days=hoy.weekday())
    nombres_dias = ['Lunes', 'Martes', 'Miércoles', 'Jueves', 'Viernes', 'Sábado', 'Domingo']
    dias = []
    for i in range(7):
        fecha_calc = inicio_semana + timedelta(days=i)
        dias.append({'nombre': nombres_dias[i], 'fecha_obj': fecha_calc, 'fecha_str': fecha_calc.strftime('%Y-%m-%d')})
    return dias

@app.route('/admin')
@login_required
def admin_panel():
    if current_user.rol != 'admin': return "Denegado", 403
    return render_template('admin.html', usuarios=Usuario.query.all())

# NUEVO: Ruta para asignar actividad
@app.route('/admin/usuario/<int:usuario_id>/asignar', methods=['GET', 'POST'])
@login_required
def admin_asignar(usuario_id):
    if current_user.rol != 'admin': return "Denegado", 403
    usuario = Usuario.query.get_or_404(usuario_id)
    if request.method == 'POST':
        usuario.disciplina_asignada_id = request.form['disciplina_id']
        dias = int(request.form['dias'])
        usuario.vencimiento = date.today() + timedelta(days=dias)
        db.session.commit()
        flash('Actividad y plan asignados correctamente.', 'success')
        return redirect(url_for('admin_panel'))
    return render_template('admin_asignar.html', usuario=usuario, disciplinas=Disciplina.query.all())

@app.route('/admin/disciplinas', methods=['GET', 'POST'])
@login_required
def admin_disciplinas():
    if current_user.rol != 'admin': return "Denegado", 403
    if request.method == 'POST':
        db.session.add(Disciplina(nombre=request.form['nombre'], descripcion=request.form['descripcion']))
        db.session.commit()
        return redirect(url_for('admin_disciplinas'))
    return render_template('admin_disciplinas.html', disciplinas=Disciplina.query.all())

@app.route('/admin/clases', methods=['GET', 'POST'])
@login_required
def admin_clases():
    if current_user.rol != 'admin': return "Denegado", 403
    if request.method == 'POST':
        disciplina_id = request.form['disciplina_id']
        dia_semana = int(request.form['dia_semana'])
        hora = request.form['hora']
        cupo = request.form['cupo']
        meses = int(request.form['meses'])
        
        # CORRECCIÓN DEL CALCULO DE DÍAS
        inicio_semana = date.today() - timedelta(days=date.today().weekday())
        fecha_clase = inicio_semana + timedelta(days=dia_semana)
        
        for i in range(meses * 4):
            fecha_str = fecha_clase.strftime('%Y-%m-%d')
            if not Clase.query.filter_by(disciplina_id=disciplina_id, fecha=fecha_str, hora=hora).first():
                db.session.add(Clase(disciplina_id=disciplina_id, fecha=fecha_str, hora=hora, cupo=cupo))
            fecha_clase += timedelta(days=7)
        db.session.commit()
        flash('Turnos generados correctamente.', 'success')
        return redirect(url_for('admin_clases'))
        
    dias_semana = obtener_dias_semana_actual()
    clases = Clase.query.filter(Clase.fecha >= dias_semana[0]['fecha_str'], Clase.fecha <= dias_semana[-1]['fecha_str']).order_by(Clase.fecha, Clase.hora).all()
    return render_template('admin_clases.html', clases=clases, disciplinas=Disciplina.query.all(), dias_semana=dias_semana)

@app.route('/admin/clases/eliminar/<int:clase_id>')
@login_required
def eliminar_clase(clase_id):
    if current_user.rol != 'admin': return "Denegado", 403
    db.session.delete(Clase.query.get_or_404(clase_id))
    db.session.commit()
    return redirect(url_for('admin_clases'))

@app.route('/admin/clases/<int:clase_id>/inscriptos')
@login_required
def admin_inscriptos(clase_id):
    if current_user.rol != 'admin': return "Denegado", 403
    return render_template('admin_inscriptos.html', clase=Clase.query.get_or_404(clase_id))

@app.route('/alumno')
@login_required
def alumno_panel():
    if current_user.rol != 'alumno': return "Denegado", 403
    
    dias_restantes = 0
    if current_user.vencimiento:
        dias_restantes = (current_user.vencimiento - date.today()).days

    dias_semana = obtener_dias_semana_actual()
    # Filtramos la grilla para que SOLO le muestre clases de su actividad asignada
    clases = Clase.query.filter(
        Clase.fecha >= dias_semana[0]['fecha_str'], 
        Clase.fecha <= dias_semana[-1]['fecha_str'],
        Clase.disciplina_id == current_user.disciplina_asignada_id
    ).order_by(Clase.fecha, Clase.hora).all()
    
    reservas_dict = {reserva.clase_id: reserva.id for reserva in current_user.mis_reservas}
    return render_template('alumno.html', clases=clases, dias_semana=dias_semana, reservas_dict=reservas_dict, dias_restantes=dias_restantes)

@app.route('/reservar/<int:clase_id>', methods=['POST'])
@login_required
def reservar_clase(clase_id):
    if current_user.rol != 'alumno': return "Denegado", 403
    clase = Clase.query.get_or_404(clase_id)
    
    if len(clase.reservas) >= clase.cupo:
        flash('La clase está llena.', 'danger')
        return redirect(url_for('alumno_panel'))
        
    db.session.add(Reserva(usuario_id=current_user.id, clase_id=clase_id))
    db.session.commit()
    flash('¡Reservado con éxito!', 'success')
    return redirect(url_for('alumno_panel'))

@app.route('/cancelar_reserva/<int:reserva_id>', methods=['POST'])
@login_required
def cancelar_reserva(reserva_id):
    if current_user.rol != 'alumno': return "Denegado", 403
    reserva = Reserva.query.get_or_404(reserva_id)
    clase = reserva.clase_reservada
    
    clase_dt = datetime.strptime(f"{clase.fecha} {clase.hora}", "%Y-%m-%d %H:%M")
    if clase_dt - datetime.now() < timedelta(minutes=30):
        flash('No podés cancelar faltando menos de 30 minutos.', 'danger')
        return redirect(url_for('alumno_panel'))
        
    db.session.delete(reserva)
    db.session.commit()
    flash('Reserva cancelada correctamente.', 'success')
    return redirect(url_for('alumno_panel'))

if __name__ == '__main__':
    app.run(debug=True)