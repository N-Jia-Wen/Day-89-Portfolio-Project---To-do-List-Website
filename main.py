from flask import Flask, render_template, redirect, url_for, flash, abort
from flask_bootstrap import Bootstrap5
from flask_sqlalchemy import SQLAlchemy
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import Integer, String, Date
from flask_wtf import FlaskForm
from wtforms import StringField, EmailField, PasswordField, DateField, SelectField
from wtfforms_buttonfield import ButtonField
from wtforms.validators import DataRequired, Email
from flask_login import UserMixin, login_user, LoginManager, login_required, current_user, logout_user
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import date


app = Flask(__name__)
app.secret_key = "Your secret key"
Bootstrap5(app)


# DB related:
class Base(DeclarativeBase):
    pass


app.config["SQLALCHEMY_DATABASE_URI"] = "sqlite:///to-do-list-website.db"
database = SQLAlchemy(model_class=Base)
database.init_app(app)


class Task(database.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(250), nullable=False)
    description: Mapped[str] = mapped_column(String(1000))
    status: Mapped[str] = mapped_column(String(100), nullable=False)
    due_date: Mapped[date] = mapped_column(Date)

    user_id: Mapped[int] = mapped_column(Integer, database.ForeignKey("user.id"))
    user = relationship("User", back_populates="tasks")


class User(UserMixin, database.Model):
    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    email: Mapped[str] = mapped_column(String(100), unique=True, nullable=False)
    hashed_password: Mapped[str] = mapped_column(String(1000), nullable=False)
    name: Mapped[str] = mapped_column(String(1000), nullable=False)
    tasks = relationship("Task", back_populates="user")


with app.app_context():
    database.create_all()


# Login manager related:
login_manager = LoginManager()
login_manager.init_app(app)


@login_manager.user_loader
def load_user(user_id):
    return database.get_or_404(User, user_id)


# Form related:
class LoginForm(FlaskForm):
    email = EmailField(label="Your email:", validators=[DataRequired(), Email()])
    password = PasswordField(label="Your password:", validators=[DataRequired()])
    submit = ButtonField(class_="btn btn-lg btn-light fw-bold border-white bg-white", default="Login")


class RegisterForm(FlaskForm):
    name = StringField(label="Your username (required):", validators=[DataRequired()])
    email = EmailField(label="Your email (required):", validators=[DataRequired(), Email()])
    password = PasswordField(label="Your password (required):", validators=[DataRequired()])
    submit = ButtonField(class_="btn btn-lg btn-light fw-bold border-white bg-white", default="Register")


class AddTaskForm(FlaskForm):
    name = StringField(label="Name of Task (required):", validators=[DataRequired()])
    description = StringField(label="Description of Task:")
    due_date = DateField(label="Due date of task:")
    submit = ButtonField(class_="btn btn-lg btn-light fw-bold border-white bg-white", default="Add Task")


class EditTaskForm(FlaskForm):
    name = StringField(label="Name of Task (required):", validators=[DataRequired()])
    description = StringField(label="Description of Task:")
    due_date = DateField(label="Due date of task:")
    status = SelectField(label="Task status (required): ",
                         choices=["Ongoing", "Completed"], validators=[DataRequired()])
    submit = ButtonField(class_="btn btn-lg btn-light fw-bold border-white bg-white", default="Add Task")


class DeleteTaskForm(FlaskForm):
    submit = ButtonField(class_="btn btn-lg btn-light fw-bold border-white bg-white", default="Delete Task")


@app.route("/")
def home():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    login_form = LoginForm()
    if login_form.validate_on_submit() is True:
        email = login_form.email.data
        password = login_form.password.data
        user = database.session.execute(database.select(User).where(User.email == email)).scalar()

        if user is None:
            flash("Sorry, user does not exist.")
        else:
            if check_password_hash(user.hashed_password, password) is True:
                login_user(user)
                return redirect(url_for('to_do_list'))
            else:
                flash("Email and password do not match.")

    return render_template("login.html", form=login_form)


@app.route("/register", methods=["GET", "POST"])
def register():
    register_form = RegisterForm()
    if register_form.validate_on_submit() is True:
        name = register_form.name.data
        email = register_form.email.data
        password = register_form.password.data
        user = database.session.execute(database.select(User).where(User.email == email)).scalar()

        if user is not None:
            flash("This user already exists.")
        else:
            hashed_password = generate_password_hash(password, salt_length=8)
            new_user = User(
                email=email,
                hashed_password=hashed_password,
                name=name
            )
            database.session.add(new_user)
            database.session.commit()
            login_user(new_user)

            return redirect(url_for('to_do_list'))

    return render_template("register.html", form=register_form)


@app.route("/to-do")
@login_required
def to_do_list():
    return render_template("to-do.html")


@app.route("/add-task", methods=["GET", "POST"])
@login_required
def add_task():
    add_task_form = AddTaskForm()
    if add_task_form.validate_on_submit() is True:
        name = add_task_form.name.data
        description = add_task_form.description.data
        due_date = add_task_form.due_date.data

        new_task = Task(
            name=name,
            description=description,
            status="Ongoing",
            due_date=due_date,
            user_id=current_user.id
        )
        database.session.add(new_task)
        database.session.commit()
        return redirect(url_for('to_do_list'))

    return render_template("add-task.html", form=add_task_form)


@app.route("/edit-task/<task_id>", methods=["GET", "POST"])
@login_required
def edit_task(task_id):
    task_to_update = database.get_or_404(Task, task_id)

    # Will give unauthorised error if current_user is not the user who created the task to be edited:
    if task_to_update.user_id == current_user.id:
        edit_task_form = EditTaskForm(
            name=task_to_update.name,
            description=task_to_update.description,
            due_date=task_to_update.due_date,
            status=task_to_update.status
        )

        if edit_task_form.validate_on_submit() is True:
            task_to_update.name = edit_task_form.name.data
            task_to_update.description = edit_task_form.description.data
            task_to_update.due_date = edit_task_form.due_date.data
            task_to_update.status = edit_task_form.status.data
            database.session.commit()

            return redirect(url_for('to_do_list'))

        else:
            return render_template("edit-task.html", form=edit_task_form)

    else:
        return redirect(url_for('unauthorised'))


@app.route("/delete-task/<task_id>", methods=["GET", "POST"])
@login_required
def delete_task(task_id):
    task_to_delete = database.get_or_404(Task, task_id)

    # Will give unauthorised error if current_user is not the user who created the task to be deleted:
    if task_to_delete.user_id == current_user.id:
        delete_task_form = DeleteTaskForm()

        if delete_task_form.validate_on_submit() is True:
            database.session.delete(task_to_delete)
            database.session.commit()

            return redirect(url_for('to_do_list'))

        else:
            return render_template("delete-task.html", form=delete_task_form)
    else:
        return redirect(url_for('unauthorised'))


@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('home'))


@app.route('/unauthorised')
def unauthorised():
    abort(401)


if __name__ == "__main__":
    app.run(debug=True)
