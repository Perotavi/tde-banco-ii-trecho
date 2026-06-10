from app import create_app
from app.extensions import db
from app.models import Usuario

app = create_app()

with app.app_context():
    usuarios = Usuario.query.all()

    for usuario in usuarios:
        usuario.definir_senha("123456")

    db.session.commit()

    print("Senhas de teste atualizadas com sucesso!")
    print("Senha de todos os usuários: 123456")