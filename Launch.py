import datetime
import os
import subprocess
import psutil
from pyunpack import Archive
import uuid

from flask import Flask, render_template, redirect, url_for, jsonify, request, send_from_directory, flash, make_response

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
    isDeployed = db.Column(db.Boolean, nullable=False)
    isInTraining = db.Column(db.Boolean, nullable=False)

    classes = db.relationship('Classes', backref='classifier')
    historyClassifier = db.relationship("History", backref='classifier')

    def __init__(self, name, isDeployed, isInTraining):
        self.name = name
        self.isDeployed = isDeployed
        self.isInTraining = isInTraining


class Classes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    classifierId = db.Column(db.Integer, db.ForeignKey("classifiers.id"), nullable=False)

    historyClasses = db.relationship('HistoryClasses', backref='class')

    def __init__(self, name, classifierId):
        self.name = name
        self.classifierId = classifierId


class TrainingEvolution(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    epoch = db.Column(db.Integer, nullable=False)
    loss = db.Column(db.Float, nullable=False)
    val_loss = db.Column(db.Float, nullable=False)
    classifierId = db.Column(db.Integer, db.ForeignKey("classifiers.id"), nullable=False)

    def __init__(self, epoch, loss, val_loss, classifierId):
        self.epoch = epoch
        self.loss = loss
        self.val_loss = val_loss
        self.classifierId = classifierId


class Users(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False, unique=True, )
    email = db.Column(db.String(200), nullable=False, unique=True, )
    password = db.Column(db.String(1000), nullable=False)
    isAdmin = db.Column(db.Boolean, nullable=False)
    lastTimeSeen = db.Column(db.DateTime, nullable=True)
    TotalImagesScanned = db.Column(db.Integer, nullable=False)
    detectPid = db.Column(db.Integer, nullable=False)
    scanProgress = db.Column(db.Integer, nullable=False)
    trainPid = db.Column(db.Integer, nullable=False)
    trainProgress = db.Column(db.Integer, nullable=False)

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
@app.route("/analyzer", methods=['GET', 'POST'])
@login_required
def analyzer():
    updatedUser = db.session.query(Users).filter(Users.id == current_user.id).first()

    if request.method == "POST":
        data = request.data.decode("utf-8")
        routePath = 'http://127.0.0.1:5000' + url_for("analyzerProgressCount")
        processPath = 'python ./MachineLearning/detect.py --classifier {} --username {} --serverPath {}' \
            .format(data, current_user.username, routePath)
        proc = subprocess.Popen(processPath)
        updatedUser.detectPid = proc.pid
        updatedUser.scanProgress = 0
        userHistory = db.session.query(History) \
            .filter(History.userId == current_user.id) \
            .filter(History.isLastScan == 1) \
            .all()
        for hist in userHistory:
            hist.isLastScan = 0
        db.session.commit()

        res = make_response(jsonify({"message": "Scan started"}), 200)
        return res

    classifierList = db.session.query(Classifiers.name).all()

    return render_template("analyzerPage/analyzerPage.html",
                           isAdminOnPage=current_user.isAdmin, classifierList=classifierList,
                           scanProgress=updatedUser.scanProgress, detectPid=updatedUser.detectPid)


@app.route("/getDetectionProgress", methods=['POST'])
@login_required
def getDetectionProgress():
    userScanProgress = db.session.query(Users.scanProgress).filter(Users.id == current_user.id).first()
    if userScanProgress.scanProgress == 100:
        userScanProgress.scanProgress = -1
        db.session.commit()
        res = make_response(jsonify({"message": 100}), 200)
        return res
    res = make_response(jsonify({"message": userScanProgress.scanProgress}), 200)
    return res


@app.route("/stopDetection", methods=['POST'])
@login_required
def stopDetection():
    userDetectPid = db.session.query(Users).filter(Users.id == current_user.id).first()
    try:
        process = psutil.Process(userDetectPid.detectPid)
        process.terminate()
    except:
        res = make_response(jsonify({"message": "Scan stopped"}), 200)
        return res
    userDetectPid.detectPid = -1
    userDetectPid.scanProgress = -1
    db.session.commit()
    res = make_response(jsonify({"message": "Scan stopped"}), 200)
    return res


@app.route("/uploadDataForAnalyzer", methods=['POST'])
@login_required
def uploadDataForAnalyzer():
    path = os.path.join('MachineLearning', 'userData', current_user.username, 'toScan')
    for file in os.listdir(path):
        os.remove(os.path.join(path, file))

    file = request.files["file"]
    fileType = '.' + file.filename.split('.')[-1]
    filename = uuid.uuid4()
    file.save(os.path.join(path, str(filename) + fileType))

    if fileType == '.zip' or fileType == '.7z' or fileType == '.rar' or fileType == '.tar':
        archineFile = os.path.join(path, str(filename) + fileType)
        Archive(archineFile).extractall(path)
        os.remove(os.path.join(path, str(filename) + fileType))
        imagesList = os.listdir(path)
        for image in imagesList:
            fileType = '.' + image.split('.')[-1]
            filename = uuid.uuid4()
            os.rename(os.path.join(path, image), os.path.join(path, str(filename) + fileType))

    res = make_response(jsonify({"message": "File uploaded"}), 200)
    return res


@app.route("/analyzerProgressCount", methods=['POST'])
def analyzerProgressCount():
    form = request.form

    classifierName = form['classifier']
    classifierId = db.session.query(Classifiers.id).filter(Classifiers.name == classifierName).first()
    username = form['username']
    userCurrent = db.session.query(Users).filter(Users.username == username).first()

    if 'imageProgress' in form:
        imageProgress = form['imageProgress']
        imageTotal = form['imageTotal']
        imageName = form['imageName']
        classesFoundList = form['classesFound'].split(',')
        classesFoundDict = {}
        for classFound in classesFoundList:
            if classFound != '':
                if classFound in classesFoundDict:
                    classesFoundDict[classFound] += 1
                else:
                    classesFoundDict[classFound] = 1

        if classesFoundDict:
            userHistory = History(imageName, datetime.date.today(), 1, classifierId.id, userCurrent.id)
            db.session.add(userHistory)

        userCurrent.scanProgress = (int(imageProgress) * 100) / int(imageTotal)
        db.session.commit()

        for key, value in classesFoundDict.items():
            classId = db.session.query(Classes.id).filter(Classes.name == key).first()
            userHistoryClasses = HistoryClasses(userHistory.id, classId.id, value)
            db.session.add(userHistoryClasses)
            db.session.commit()

        return make_response('Image added', 200)

    imagesScanned = form['imagesScanned']

    userCurrent.detectPid = -1
    total = userCurrent.TotalImagesScanned + int(imagesScanned)
    userCurrent.TotalImagesScanned = total
    db.session.commit()

    return make_response('Scan complete', 200)


@app.route("/analyzerShowResult")
@login_required
def analyzerShowResult():
    classifierList = db.session.query(Classifiers.name).all()
    classList = db.session.query(Classes.name).distinct(Classes.name).all()
    firstFiveClassList = []
    for i in range(0, 5):
        if len(classList) != 0:
            firstFiveClassList.append(classList.pop(0))

    imagePaths = db.session.query(History.imagePath, History.id) \
        .filter(History.userId == current_user.id) \
        .filter(History.isLastScan == 1) \
        .group_by(History.id) \
        .all()

    return render_template("historyPage.html", isAdminOnPage=current_user.isAdmin,
                           classifierList=classifierList,
                           classList=classList,
                           firstFiveClassList=firstFiveClassList,
                           imagePaths=imagePaths,
                           searchResultNumber=len(imagePaths),
                           givenUsername=current_user.username)


# ----------------------Classifiers Region
@app.route("/classifiers")
@login_required
def classifiers():
    if current_user.isAdmin:
        classifierList = db.session.query(Classifiers.name, Classifiers.isDeployed).all()
        return render_template("classifiersPage/adminClassifiersPage.html",
                               classifierList=classifierList)
    return render_template("classifiersPage/userClassifiersPage.html")


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


@app.route("/updateDeployedClassifiers", methods=['POST'])
@login_required
def updateDeployedClassifiers():
    if not current_user.isAdmin:
        return "<h1>Not authorized</h1>"

    classifierFilterList = request.form.getlist("classifierCheckBox")
    classifierList = db.session.query(Classifiers).all()
    for classifier in classifierList:
        if classifier.name in classifierFilterList:
            classifier.isDeployed = True
        else:
            classifier.isDeployed = False

    db.session.commit()
    return redirect(url_for('classifiers'))


@app.route("/updateClassifierList", methods=['POST'])
@login_required
def updateClassifierList():
    if not current_user.isAdmin:
        return "<h1>Not authorized</h1>"
    filterList = []
    if request.form['classifier'] != '':
        filterList = {Classifiers.name.contains(request.form['classifier'])}

    classifierList = db.session.query(Classifiers.name, Classifiers.isDeployed) \
        .filter(*filterList) \
        .all()

    return render_template("classifiersPage/adminClassifierSectionPage.html",
                           classifierList=classifierList)


@app.route("/showClassifierDetails", methods=['POST'])
@login_required
def showClassifierDetails():
    if not current_user.isAdmin:
        return "<h1>Not authorized</h1>"

    classifierDetails = db.session.query(Classifiers) \
        .filter(Classifiers.name == request.form['classifier']) \
        .first()
    classList = db.session.query(Classes.name).filter(Classes.classifierId == classifierDetails.id).all()
    classifierEvolutionChart = db.session.query(TrainingEvolution). \
        filter(TrainingEvolution.classifierId == classifierDetails.id).all()

    return render_template("classifiersPage/adminClassifierDetailSection.html",
                           classifierDetails=classifierDetails, classList=classList,
                           classifierEvolutionChart=classifierEvolutionChart)


@app.route("/uploadDataForTraining", methods=['POST'])
@login_required
def uploadDataForTraining():
    classifierName = request.form['classifier']
    path = os.path.join('MachineLearning', 'classifiers', classifierName)

    file = request.files["file"]
    file.save(os.path.join(path, file.filename))
    archiveFile = os.path.join(path, file.filename)
    Archive(archiveFile).extractall(path)
    os.remove(os.path.join(path, file.filename))
    transformDatasetScriptPath = 'python ' + \
                                 os.path.join('MachineLearning', "convertPascalVocToTfrecord.py") + \
                                 " --classifier {}".format(classifierName)
    subprocess.run(transformDatasetScriptPath)

    res = make_response(jsonify({"message": "File uploaded"}), 200)
    return res


@app.route("/trainClassifier", methods=['POST'])
@login_required
def trainClassifier():
    batch_size = 1
    epoch = 20
    adminUser = db.session.query(Users).filter(Users.id == current_user.id).first()
    if not adminUser.isAdmin:
        return "Permission Denied"
    data = request.form
    routePath = 'http://127.0.0.1:5000' + url_for("trainingProgressCount")
    if data['trainingType'] == 'clean':
        processPath = 'python ' + os.path.join('MachineLearning', 'train.py') + \
                      ' --batch_size {} --epochs {} --mode fit --transfer none'.format(batch_size, epoch) + \
                      ' --classifier {} --username {} --serverPath {}'.format(data['classifier'],
                                                                              current_user.username,
                                                                              routePath)
        classifierId = db.session.query(Classifiers.id).filter(Classifiers.name == data['classifier']).first()
        db.session.query(TrainingEvolution).filter(TrainingEvolution.classifierId == classifierId.id).delete()
    elif data['trainingType'] == 'fine_tune':
        checkpointPath = os.path.join('MachineLearning', 'classifiers', data['classifier'], 'checkpoints')
        checkpointList = os.listdir(checkpointPath)
        checkpointList.remove('checkpoint')
        weights = os.path.join(checkpointPath,
                               checkpointList[-1].split('.')[0] + '.' + checkpointList[-1].split('.')[1])
        processPath = 'python ' + os.path.join('MachineLearning', 'train.py') + \
                      ' --batch_size {} --epochs {} --mode eager_fit --transfer fine_tune'.format(batch_size, epoch) + \
                      ' --weights {}'.format(weights) + \
                      ' --classifier {} --username {} --serverPath {}'.format(data['classifier'],
                                                                              current_user.username,
                                                                              routePath)
    else:
        processPath = 'python ' + os.path.join('MachineLearning', 'train.py') + \
                      ' --batch_size {} --epochs {} --mode fit --transfer darknet'.format(batch_size, epoch) + \
                      ' --classifier {} --username {} --serverPath {}'.format(data['classifier'],
                                                                              current_user.username,
                                                                              routePath)
        classifierId = db.session.query(Classifiers.id).filter(Classifiers.name == data['classifier']).first()
        db.session.query(TrainingEvolution).filter(TrainingEvolution.classifierId == classifierId.id).delete()

    proc = subprocess.Popen(processPath)
    adminUser.trainPid = proc.pid
    adminUser.trainProgress = 0
    # TODO: add only one person can train one classifier
    # TODO: dont dispay in training Classifers to user using isTraining
    db.session.commit()

    res = make_response(jsonify({"message": "Training started"}), 200)
    return res


@app.route("/trainingProgressCount", methods=['POST'])
def trainingProgressCount():
    form = request.form

    classifierName = form['classifier']
    classifierId = db.session.query(Classifiers.id).filter(Classifiers.name == classifierName).first()
    username = form['username']
    userCurrent = db.session.query(Users).filter(Users.username == username).first()

    if 'loss' in form:
        loss = form['loss']
        val_loss = form['val_loss']
        epoch = form['epoch']
        total_epoch = form['total_epoch']

        userCurrent.trainProgress = (int(epoch) * 100) / int(total_epoch)
        db.session.commit()

        newTrainingEvaluation = TrainingEvolution(int(epoch), float(loss), float(val_loss), classifierId.id)
        db.session.add(newTrainingEvaluation)
        db.session.commit()

        return make_response('Evaluation added', 200)

    userCurrent.trainPid = -1
    db.session.commit()

    return make_response('Training complete', 200)


@app.route("/getTrainingProgress", methods=['POST'])
@login_required
def getTrainingProgress():
    classifierTrainingProgress = db.session.query(Users).filter(Users.id == current_user.id).first()
    if classifierTrainingProgress.trainProgress == 100:
        classifierTrainingProgress.trainProgress = -1
        db.session.commit()
        res = make_response(jsonify({"message": 100}), 200)
        return res
    res = make_response(jsonify({"message": classifierTrainingProgress.trainProgress}), 200)
    return res


@app.route("/stopTraining", methods=['POST'])
@login_required
def stopTraining():
    userTrainingPid = db.session.query(Users).filter(Users.id == current_user.id).first()
    try:
        process = psutil.Process(userTrainingPid.trainPid)
        process.terminate()
    except:
        res = make_response(jsonify({"message": "Training stopped"}), 200)
        return res
    userTrainingPid.trainPid = -1
    userTrainingPid.trainProgress = -1
    db.session.commit()
    res = make_response(jsonify({"message": "Training stopped"}), 200)
    return res


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
    imageUrl = os.path.join('.', 'MachineLearning', 'userData', username, 'output')
    return send_from_directory(imageUrl, filename)


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
