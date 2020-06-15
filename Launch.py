import datetime
from flask import Flask, render_template, redirect, url_for, jsonify, request
from flask_sqlalchemy import SQLAlchemy

app = Flask(__name__)
app.config['SECRET_KEY'] = 'TOCHANGE'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///database\\database.sqlite3'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)


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

    history = db.relationship('History', backref='user')

    def __init__(self, username, email, password, isAdmin):
        self.username = username
        self.email = email
        self.password = password
        self.isAdmin = isAdmin


class History(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    imagePath = db.Column(db.Text, nullable=False)
    scanDate = db.Column(db.Date, nullable=False)
    isLastScan = db.Column(db.Boolean, nullable=False)
    classifierId = db.Column(db.Integer, db.ForeignKey("classifiers.id"), nullable=False)
    userId = db.Column(db.Integer, db.ForeignKey("users.id"), nullable=False)

    historyClasses = db.relationship('HistoryClasses', backref='history')

    def __init__(self, imagePath, scanDate, isLastScan, userId):
        self.imagePath = imagePath
        self.scanDate = scanDate
        self.isLastScan = isLastScan
        self.userId = userId


class HistoryClasses(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    historyId = db.Column(db.Integer, db.ForeignKey("history.id"), nullable=False)
    classId = db.Column(db.Integer, db.ForeignKey("classes.id"), nullable=False)
    numberOfClasses = db.Column(db.Integer, nullable=False)

    def __init__(self, historyId, classId):
        self.historyId = historyId
        self.classId = classId


# ----------------------Models Region

# ----------------------Temp Region
# db.drop_all()
# db.create_all()

isAdminSet = False


# ----------------------Temp Region


@app.route("/")
def home():
    # return render_template("login.html")
    return redirect(url_for("history"))


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

    if request.method == 'POST':
        classifierFilterName = request.form.get("classifierName")
        classFilterList = request.form.getlist("classCheckBox")
        takenDateString = request.form.get("date")
        usernameId = 1  # TODO Set Session Username

        filterList = [History.userId == usernameId]

        if classifierFilterName != 'All Classifiers':
            filterList.append(Classifiers.name == classifierFilterName)

        if takenDateString != '':
            takenDateFilter = datetime.datetime.strptime(takenDateString, '%d/%m/%Y')
            filterList.append(History.scanDate == takenDateFilter.date())

        # for classType in classFilterList:
        #     filterList.append()

        imagePaths = db.session.query(History, Classifiers) \
            .outerjoin(Classifiers, Classifiers.id == History.classifierId) \
            .filter(*filterList) \
            .all()

        return render_template("historyPage.html", isAdminOnPage=isAdminSet,
                               classifierList=classifierList,
                               classList=classList,
                               firstFiveClassList=firstFiveClassList)
    else:
        return render_template("historyPage.html", isAdminOnPage=isAdminSet,
                               classifierList=classifierList,
                               classList=classList,
                               firstFiveClassList=firstFiveClassList)


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
@app.route("/profile")
def profile():
    return render_template("profilePage.html", isAdminOnPage=isAdminSet)


# ----------------------Profile Region

if __name__ == '__main__':
    app.run(threaded=True, debug=True)
    # app.run(host='0.0.0.0',port=5000, threaded=True, debug=True)
