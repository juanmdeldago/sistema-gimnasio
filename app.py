from flask import Flask, render_template

app = Flask(__name__)

# Base de datos temporal para probar la vista de Socios
socios = [
    {"id": 1, "nombre": "Matias", "apellido": "Zamorano", "estado": "Activo"},
    {"id": 2, "nombre": "Maria", "apellido": "Sarmiento", "estado": "Pendiente"}
]

@app.route('/')
def inicio():
    # Enviamos los socios a la plantilla web
    return render_template('index.html', lista_socios=socios)

if __name__ == '__main__':
    app.run(debug=True)