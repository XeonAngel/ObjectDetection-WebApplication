import datetime
import os

from flask import Flask, render_template, redirect, url_for, jsonify, request, send_from_directory, flash

from werkzeug.security import generate_password_hash, check_password_hash
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user

from flask_sqlalchemy import SQLAlchemy

from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

from flask_bootstrap import Bootstrap
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField
from wtforms.fields.html5 import EmailField
from wtforms.validators import InputRequired, Email, Length, EqualTo, ValidationError

# from MachineLearning.detect import main

app = Flask(__name__)  # TODO: Modificat Secretkey To ceva gen b'_5#y2L"F4Q8z\n\xec]/' creat automat
app.config.from_pyfile('config.cfg')
db = SQLAlchemy(app)
mail = Mail(app)
Bootstrap(app)
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
ulrSerializer = URLSafeTimedSerializer(app.config['SECRET_KEY'])


# ----------------------Models Region
class Classifiers(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), unique=True, nullable=False)

    classes = db.relationship('Classes', backref='classifier')
    historyClassifier = db.relationship("History", backref='classifier')

    def __init__(self, name):
        self.name = name


class Classes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    classifierId = db.Column(db.Integer, db.ForeignKey("classifiers.id"), nullable=False)

    historyClasses = db.relationship('HistoryClasses', backref='class')

    def __init__(self, name, classifierId):
        self.name = name
        self.classifierId = classifierId


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True, )
    email = db.Column(db.String(200), nullable=False, unique=True, )
    password = db.Column(db.String(1000), nullable=False)
    isAdmin = db.Column(db.Boolean, nullable=False)
    lastTimeSeen = db.Column(db.DateTime, nullable=True)
    TotalImagesScanned = db.Column(db.Integer, nullable=False)

    history = db.relationship('History', backref='user')  # TODO: Astea ar trebui sa fie lazy='dynamic'

    def __init__(self, username, email, password, isAdmin, TotalImagesScanned):
        self.username = username
        self.email = email
        self.password = password
        self.isAdmin = isAdmin
        self.TotalImagesScanned = TotalImagesScanned


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imagePath = db.Column(db.Text, nullable=False)
    scanDate = db.Column(db.Date, nullable=False)
    isLastScan = db.Column(db.Boolean, nullable=False)
    classifierId = db.Column(db.Integer, db.ForeignKey("classifiers.id"), nullable=False)
    userId = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    historyClasses = db.relationship('HistoryClasses', backref='history')

    def __init__(self, imagePath, scanDate, isLastScan, classifierId, userId):
        self.imagePath = imagePath
        self.scanDate = scanDate
        self.isLastScan = isLastScan
        self.classifierId = classifierId
        self.userId = userId


class HistoryClasses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    historyId = db.Column(db.Integer, db.ForeignKey("history.id"), nullable=False)
    classId = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    numberOfClasses = db.Column(db.Integer, nullable=False)

    def __init__(self, historyId, classId, numberOfClasses):
        self.historyId = historyId
        self.classId = classId
        self.numberOfClasses = numberOfClasses


# ----------------------Forms Region
class RegisterForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=8, max=50)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=10, max=100)])
    # TODO de pus ConfirmPassword
    submit = SubmitField('Register')

    def validate_password(self, field):
        password = field.data
        if not (any(x.isupper() for x in password) and any(x.islower() for x in password)
                and any(x.isdigit() for x in password) and any(not c.isalnum() for c in password)):
            raise ValidationError(
                'Password must contain at least 1 uppercase character, at least 1 lowercase character, at least 1 '
                'digit and at least 1 special character.')


class LoginForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=8, max=50)])
    password = PasswordField('Password', validators=[InputRequired(), Length(min=10, max=100)])
    remember = BooleanField('Remember me')
    submit = SubmitField('Login')


class ResetPasswordForm(FlaskForm):
    email = EmailField('Email', validators=[InputRequired(), Email()])
    submit = SubmitField('New password')


class NewPasswordForm(FlaskForm):
    newPassword = PasswordField('New Password', validators=[InputRequired(), Length(min=10, max=100)])
    confirmPassword = PasswordField('Repeat Password', validators=[InputRequired(), Length(min=10, max=100),
                                                                   EqualTo('newPassword',
                                                                           message='Passwords must match')])
    submit = SubmitField('Reset Password')

    def validate_newPassword(self, field):
        password = field.data
        if not (any(x.isupper() for x in password) and any(x.islower() for x in password)
                and any(x.isdigit() for x in password) and any(not c.isalnum() for c in password)):
            raise ValidationError(
                'Password must contain at least 1 uppercase character, at least 1 lowercase character, at least 1 '
                'digit and at least 1 special character.')


class ProfileForm(FlaskForm):
    username = StringField('Username', validators=[InputRequired(), Length(min=8, max=50)])
    email = EmailField('Email', validators=[InputRequired(), Email()])
    password = PasswordField('Password')
    confirmPassword = PasswordField('Repeat Password',
                                    validators=[EqualTo('password', message='Passwords must match')])
    submit = SubmitField('Save Changes')

    def validate_password(self, field):
        password = field.data
        if password != "":
            if not (any(x.isupper() for x in password) and any(x.islower() for x in password)
                    and any(x.isdigit() for x in password) and any(not c.isalnum() for c in password)):
                raise ValidationError(
                    'Password must contain at least 1 uppercase character, at least 1 lowercase character, at least 1 '
                    'digit and at least 1 special character.')


# ----------------------Temp Region
# db.drop_all()
# db.create_all()

tempUsers = db.session.query(Users.username).all()
for user in tempUsers:
    userPath = os.path.join('.', 'MachineLearning', 'userData', user.username)
    if not os.path.exists(os.path.join(userPath, 'toScan')):
        os.makedirs(os.path.join(userPath, 'toScan'))
    if not os.path.exists(os.path.join(userPath, 'output')):
        os.makedirs(os.path.join(userPath, 'output'))

tempClassifiers = db.session.query(Classifiers.name).all()
for classifier in tempClassifiers:
    classifierPath = os.path.join('.', 'MachineLearning', 'classifiers', classifier.name)
    if not os.path.exists(classifierPath):
        os.makedirs(classifierPath)


# ----------------------Start Region
@login_manager.user_loader
def load_user(user_id):
    return Users.query.get(int(user_id))


@app.route("/")
def home():
    if current_user.is_authenticated:
        if current_user.isAdmin:
            return redirect(url_for('classifiers'))
        else:
            return redirect(url_for('analyzer'))
    return redirect(url_for("login"))


# ----------------------Analyzer Region
@app.route("/analyzer")
@login_required
def analyzer():
    return render_template("analyzerPage.html", isAdminOnPage=current_user.isAdmin)


# ----------------------Classifiers Region
@app.route("/classifiers")
@login_required
def classifiers():
    if current_user.isAdmin:
        return render_template("adminClassifiersPage.html")
    return render_template("userClassifiersPage.html")


@app.route("/userclassifierslist/<classToFind>")
@login_required
def userclassifierslist(classToFind):
    # TODO: Move Classifers to another iframe just add mode than one page can see and test it
    # TODO: Alphabetic Sort
    if classToFind == "all":
        classifierList = db.session.query(Classifiers.name).all()
    else:
        classifierList = db.session.query(Classifiers.name) \
            .outerjoin(Classes, Classifiers.id == Classes.classifierId) \
            .filter(Classes.name.contains(classToFind)) \
            .filter(Classes.name is not None) \
            .distinct(Classifiers.name) \
            .all()
    return render_template("iframes/userClassifiersIframe.html", classifierList=classifierList)


@app.route("/classesforclassifier/<classifier>")
@login_required
def classesforclassifier(classifier):
    if classifier == "none":
        return render_template("iframes/userClassesListIframe.html", classList="")
    else:
        classList = db.session.query(Classes.name) \
            .outerjoin(Classifiers, Classifiers.id == Classes.classifierId) \
            .filter(Classifiers.name.contains(classifier)) \
            .filter(Classifiers.name is not None).all()
    return render_template("iframes/userClassesListIframe.html", classList=classList)


# ----------------------History Region
@app.route("/history", methods=['GET', 'POST'])
@login_required
def history():
    classifierList = db.session.query(Classifiers.name).all()
    classList = db.session.query(Classes.name).distinct(Classes.name).all()
    firstFiveClassList = []
    for i in range(0, 5):
        if len(classList) != 0:
            firstFiveClassList.append(classList.pop(0))

    if request.method == 'POST':
        classifierFilterName = request.form.get("classifierName")
        classFilterList = request.form.getlist("classCheckBox")
        takenDateString = request.form.get("date")

        filterList = [History.userId == current_user.id]

        if classifierFilterName != 'All Classifiers':
            filterList.append(Classifiers.name == classifierFilterName)

        if takenDateString != '':
            takenDateFilter = datetime.datetime.strptime(takenDateString, '%d/%m/%Y')
            filterList.append(History.scanDate == takenDateFilter.date())

        if classFilterList:
            filterList.append(Classes.name.in_(classFilterList))
            imagePaths = db.session.query(History.imagePath) \
                .outerjoin(Classifiers, Classifiers.id == History.classifierId) \
                .outerjoin(HistoryClasses, HistoryClasses.historyId == History.id) \
                .outerjoin(Classes, Classes.id == HistoryClasses.classId) \
                .filter(*filterList) \
                .group_by(History.id) \
                .having(db.func.count(HistoryClasses.classId.distinct()) == len(set(classFilterList))) \
                .all()
        else:
            imagePaths = db.session.query(History.imagePath, History.id) \
                .outerjoin(Classifiers, Classifiers.id == History.classifierId) \
                .outerjoin(HistoryClasses, HistoryClasses.historyId == History.id) \
                .outerjoin(Classes, Classes.id == HistoryClasses.classId) \
                .filter(*filterList) \
                .group_by(History.id) \
                .all()

        return render_template("historyPage.html", isAdminOnPage=current_user.isAdmin,
                               classifierList=classifierList,
                               classList=classList,
                               firstFiveClassList=firstFiveClassList,
                               imagePaths=imagePaths,
                               searchResultNumber=len(imagePaths),
                               givenUsername=current_user.username)
    else:
        return render_template("historyPage.html", isAdminOnPage=current_user.isAdmin,
                               classifierList=classifierList,
                               classList=classList,
                               firstFiveClassList=firstFiveClassList,
                               imagePaths="",
                               searchResultNumber=-1,
                               givenUsername=current_user.username)


@app.route("/historyImage/<username>/<filename>")
@login_required
def giveImageFromDirectory(username, filename):
    if current_user.username != username:
        return "<h1>Not authorized</h1>"
    imageUrl = username + "/" + filename
    return send_from_directory("MachineLearning/output/", imageUrl)


@app.route("/historyImageClasses", methods=['POST'])
@login_required
def giveClassesForImage():
    classList = db.session.query(HistoryClasses.numberOfClasses, Classes.name) \
        .outerjoin(Classes, Classes.id == HistoryClasses.classId) \
        .filter(HistoryClasses.historyId == request.form['historyId']) \
        .all()
    return render_template("historyPage/historyPageImagePreviewClasses.html", classList=classList)


@app.route("/updateHistoryClasses", methods=['POST'])
@login_required
def updateHistoryClasses():
    filterList = []
    if request.form['classifier'] != 'All Classifiers':
        filterList = {Classifiers.name == request.form['classifier']}

    classList = db.session.query(Classes.name) \
        .outerjoin(Classifiers, Classifiers.id == Classes.classifierId) \
        .filter(*filterList) \
        .all()

    firstFiveClassList = []
    for i in range(0, 5):
        if len(classList) != 0:
            firstFiveClassList.append(classList.pop(0))

    return render_template("historyPage/historyPageClasses.html",
                           classList=classList,
                           firstFiveClassList=firstFiveClassList)


# ----------------------Users Region
@app.route("/users")
@login_required
def users():
    # TODO: Toate functiile ce tin de admin sa verifica daca este un admin setat
    # TODO: De setat titlu la fiecare pagina
    if not current_user.isAdmin:
        return "<h1>Not authorized</h1>"

    userList = db.session.query(Users.id, Users.username, Users.email, Users.lastTimeSeen, Users.TotalImagesScanned,
                                Classifiers.name) \
        .outerjoin(History, History.userId == Users.id) \
        .outerjoin(Classifiers, Classifiers.id == History.classifierId) \
        .group_by(Users.username) \
        .filter(Users.isAdmin == 0) \
        .all()

    return render_template("usersPage.html", userList=userList)


@app.route("/usersDelete/<userId>", methods=['GET'])
@login_required
def usersDelete(userId):
    if not current_user.isAdmin:
        return "<h1>Not authorized</h1>"

    user = Users.query.get(userId)
    db.session.delete(user)
    db.session.commit()
    return redirect(url_for('users'))


@app.route("/usersInsert", methods=['POST'])
@login_required
def usersInsert():
    if not current_user.isAdmin:
        return "<h1>Not authorized</h1>"

    email = request.form['email']
    token = ulrSerializer.dumps(email)
    message = Message('Create new account', sender='object.selector@gmail.com', recipients=[email])
    link = url_for('createNewUser', token=token, _external=True)
    message.body = 'Link to create new account is: {}\r\nThis link will expire in 24 hours.'.format(link)
    mail.send(message)

    flash("Invitation mail was send successfully")

    return redirect(url_for('users'))


@app.route("/createNewUser/<token>", methods=['GET', 'POST'])
def createNewUser(token):
    form = RegisterForm()

    if request.method == 'GET':
        try:
            email = ulrSerializer.loads(token, max_age=86400)
        except SignatureExpired:
            flash("The link has expired")
            return render_template("register_loginPages/registerPage.html", form=form, token=token)
        return render_template("register_loginPages/registerPage.html", form=form, token=token)

    if form.validate_on_submit():
        try:
            email = ulrSerializer.loads(token, max_age=86400)
        except SignatureExpired:
            flash("The link has expired")
            return render_template("register_loginPages/registerPage.html", form=form, token=token)
        user = Users(form.username.data, email, generate_password_hash(form.password.data), 0, 0)
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('login'))
    return render_template("register_loginPages/registerPage.html", form=form, token=token)


# ----------------------Login/Logout Region
@app.route("/login", methods=['GET', 'POST'])
def login():
    loginForm = LoginForm()
    newPasswordForm = ResetPasswordForm()

    if request.method == 'GET':
        return render_template("register_loginPages/loginPage.html",
                               loginForm=loginForm,
                               newPasswordForm=newPasswordForm)

    if loginForm.validate_on_submit():
        user = db.session.query(Users) \
            .filter(Users.username == loginForm.username.data) \
            .first()

        if user:
            if check_password_hash(user.password, loginForm.password.data):
                login_user(user, remember=loginForm.remember.data)
                user.lastTimeSeen = datetime.datetime.now()
                db.session.commit()
                if current_user.isAdmin:
                    return redirect(url_for("classifiers"))
                else:
                    return redirect(url_for("analyzer"))
            else:
                flash("Wrong username or password")
                return render_template("register_loginPages/loginPage.html",
                                       loginForm=loginForm,
                                       newPasswordForm=newPasswordForm)
        else:
            flash("Wrong username or password")
            return render_template("register_loginPages/loginPage.html",
                                   loginForm=loginForm,
                                   newPasswordForm=newPasswordForm)

    return render_template("register_loginPages/loginPage.html", loginForm=loginForm, newPasswordForm=newPasswordForm)


@app.route("/resetPassword", methods=['POST'])
def resetPassword():
    newPasswordForm = ResetPasswordForm()
    email = newPasswordForm.email.data
    if newPasswordForm.validate_on_submit():
        user = db.session.query(Users).filter(Users.email == email).first()
        if user:
            token = ulrSerializer.dumps(email)
            message = Message('Reset Password', sender='object.selector@gmail.com', recipients=[email])
            link = url_for('newPassword', token=token, _external=True)
            message.body = 'Reset your password at this link: {}\r\nThis link will expire in 1 hours.'.format(link)
            mail.send(message)
            flash("Check your mail inbox for password reset link.")
            return redirect(url_for('login'))
        flash("Email not found")
        return redirect(url_for('login'))
    return redirect(url_for('login'))


@app.route("/resetPassword/<token>", methods=['GET', 'POST'])
def newPassword(token):
    newPasswordForm = NewPasswordForm()

    if request.method == 'GET':
        try:
            email = ulrSerializer.loads(token, max_age=3600)
        except SignatureExpired:
            flash("The link has expired")
            return render_template("register_loginPages/resetPasswordPage.html", newPasswordForm=newPasswordForm,
                                   token=token)
        return render_template("register_loginPages/resetPasswordPage.html", newPasswordForm=newPasswordForm,
                               token=token)

    if newPasswordForm.validate_on_submit():
        try:
            email = ulrSerializer.loads(token, max_age=3600)
        except SignatureExpired:
            flash("The link has expired")
            return render_template("register_loginPages/resetPasswordPage.html", newPasswordForm=newPasswordForm,
                                   token=token)
        user = Users.query.filter_by(email=email).first()
        user.password = generate_password_hash(newPasswordForm.newPassword.data)
        db.session.commit()
        flash("Password changed successfully")
        return redirect(url_for('login'))
    return render_template("register_loginPages/resetPasswordPage.html", newPasswordForm=newPasswordForm, token=token)


@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))


# ----------------------Profile Region
@app.route("/profile", methods=['GET', 'POST'])
@login_required
def profile():
    profileForm = ProfileForm()

    if request.method == 'GET':
        user = Users.query.filter_by(id=current_user.id).first()
        profileForm.username.data = user.username
        profileForm.email.data = user.email
        return render_template("profilePage/profilePage.html", isAdminOnPage=current_user.isAdmin,
                               profileForm=profileForm)

    if profileForm.validate_on_submit():
        user = Users.query.filter_by(id=current_user.id).first()
        user.username = profileForm.username.data
        user.email = profileForm.email.data
        if profileForm.password.data:
            user.password = generate_password_hash(profileForm.password.data)

        db.session.commit()
        flash("Profile saved!")
        profileForm = ProfileForm()
        profileForm.username.data = user.username
        profileForm.email.data = user.email
        return render_template("profilePage/profilePage.html", isAdminOnPage=current_user.isAdmin,
                               profileForm=profileForm)
    return render_template("profilePage/profilePage.html", isAdminOnPage=current_user.isAdmin,
                           profileForm=profileForm)


if __name__ == '__main__':
    app.run(threaded=True, debug=True)
    # app.run(host='0.0.0.0',port=5000, threaded=True, debug=True)
