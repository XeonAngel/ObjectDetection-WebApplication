import datetime
from flask import Flask, render_template, redirect, url_for, jsonify, request, send_from_directory, flash
from flask_sqlalchemy import SQLAlchemy
from flask_mail import Mail, Message
from itsdangerous import URLSafeTimedSerializer, SignatureExpired

app = Flask(__name__)  # TODO: Modificat Secretkey To ceva gen b'_5#y2L"F4Q8z\n\xec]/'
app.config.from_pyfile('config.cfg')
db = SQLAlchemy(app)
mail = Mail(app)
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


class Users(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(200), nullable=False)
    password = db.Column(db.String(1000), nullable=False)
    isAdmin = db.Column(db.Boolean, nullable=False)
    lastTimeSeen = db.Column(db.DateTime, nullable=True)
    TotalImagesScanned = db.Column(db.Integer, nullable=False)

    history = db.relationship('History', backref='user')

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


# ----------------------Models Region

# ----------------------Temp Region
# db.drop_all()
# db.create_all()

isAdminSet = True


# ----------------------Temp Region


@app.route("/")
def home():
    # return render_template("login.html")
    return redirect(url_for("users"))


# ----------------------Analyzer Region
@app.route("/analyzer")
def analyzer():
    return render_template("analyzerPage.html", isAdminOnPage=isAdminSet)


# ----------------------Analyzer Region


# ----------------------Classifiers Region
@app.route("/classifiers")
def classifiers():
    if isAdminSet:
        return render_template("adminClassifiersPage.html")
    return render_template("userClassifiersPage.html")


@app.route("/userclassifierslist/<classToFind>")
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
def classesforclassifier(classifier):
    if classifier == "none":
        return render_template("iframes/userClassesListIframe.html", classList="")
    else:
        classList = db.session.query(Classes.name) \
            .outerjoin(Classifiers, Classifiers.id == Classes.classifierId) \
            .filter(Classifiers.name.contains(classifier)) \
            .filter(Classifiers.name is not None).all()
    return render_template("iframes/userClassesListIframe.html", classList=classList)


# ----------------------Classifiers Region


# ----------------------History Region
@app.route("/history", methods=['GET', 'POST'])
def history():
    classifierList = db.session.query(Classifiers.name).all()
    classList = db.session.query(Classes.name).distinct(Classes.name).all()
    firstFiveClassList = []
    for i in range(0, 5):
        if len(classList) != 0:
            firstFiveClassList.append(classList.pop(0))

    usernameId = 1  # TODO Set Session Username
    username = 'Admin'  # TODO Set Session Username

    if request.method == 'POST':
        classifierFilterName = request.form.get("classifierName")
        classFilterList = request.form.getlist("classCheckBox")
        takenDateString = request.form.get("date")

        filterList = [History.userId == usernameId]

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

        return render_template("historyPage.html", isAdminOnPage=isAdminSet,
                               classifierList=classifierList,
                               classList=classList,
                               firstFiveClassList=firstFiveClassList,
                               imagePaths=imagePaths,
                               searchResultNumber=len(imagePaths),
                               givenUsername=username)
    else:
        return render_template("historyPage.html", isAdminOnPage=isAdminSet,
                               classifierList=classifierList,
                               classList=classList,
                               firstFiveClassList=firstFiveClassList,
                               imagePaths="",
                               searchResultNumber=-1,
                               givenUsername=username)


@app.route("/historyImage/<username>/<filename>")
def giveImageFromDirectory(username, filename):
    imageUrl = username + "/" + filename
    return send_from_directory("MachineLearning/output/", imageUrl)


@app.route("/historyImageClasses", methods=['POST'])
def giveClassesForImage():
    classList = db.session.query(HistoryClasses.numberOfClasses, Classes.name) \
        .outerjoin(Classes, Classes.id == HistoryClasses.classId) \
        .filter(HistoryClasses.historyId == request.form['historyId']) \
        .all()
    return render_template("historyPage/historyPageImagePreviewClasses.html", classList=classList)


@app.route("/updateHistoryClasses", methods=['POST'])
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


# ----------------------History Region


# ----------------------Profile Region
@app.route("/users")
def users():
    # TODO: Toate functiile ce tin de admin sa verifica daca este un admin setat
    # TODO: De setat titlu la fiecare pagina
    userList = db.session.query(Users.id, Users.username, Users.email, Users.lastTimeSeen, Users.TotalImagesScanned,
                                Classifiers.name) \
        .outerjoin(History, History.userId == Users.id) \
        .outerjoin(Classifiers, Classifiers.id == History.classifierId) \
        .group_by(Users.username) \
        .filter(Users.isAdmin == 0) \
        .all()

    return render_template("usersPage.html", userList=userList)


@app.route("/usersDelete/<userId>")
def usersDelete(userId):
    return


@app.route("/usersInsert", methods=['POST'])
def usersInsert():
    email = request.form['email']
    token = ulrSerializer.dumps(email)
    message = Message('Create new account', sender='object.selector@gmail.com', recipients=[email])
    link = url_for('createNewUser', token=token, _external=True)
    message.body = 'Link to create new account is: {}\r\nThis link will expire in 24 hours.'.format(link)
    mail.send(message)

    flash("Invitation mail was send successfully")

    return redirect(url_for('users'))

@app.route("/createNewUser/<token>")
def createNewUser(token):
    try:
        email = ulrSerializer.loads(token, max_age=86400)
    except SignatureExpired:
        return '<h1>The link has expired</h1>'

    
    return redirect(url_for('users'))# TODO: Redirect to login


# ----------------------Profile Region


# ----------------------Profile Region
@app.route("/profile")
def profile():
    return render_template("profilePage.html", isAdminOnPage=isAdminSet)


# ----------------------Profile Region

if __name__ == '__main__':
    app.run(threaded=True, debug=True)
    # app.run(host='0.0.0.0',port=5000, threaded=True, debug=True)
