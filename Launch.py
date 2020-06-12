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

    def __init__(self, name):
        self.name = name


class Classes(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    classifierId = db.Column(db.Integer, db.ForeignKey("classifiers.id"), nullable=False)

    def __init__(self, name, classifierId):
        self.name = name
        self.classifierId = classifierId


# ----------------------Models Region

# ----------------------Temp Region
# db.drop_all()
# db.create_all()

isAdmin = False


# ----------------------Temp Region


@app.route("/")
def home():
    # return render_template("login.html")
    return redirect(url_for("history"))


# ----------------------Analyzer Region
@app.route("/analyzer")
def analyzer():
    return render_template("analyzerPage.html", isAdminOnPage=isAdmin)


# ----------------------Analyzer Region


# ----------------------Classifiers Region
@app.route("/classifiers")
def classifiers():
    if isAdmin:
        return render_template("adminClassifiersPage.html")
    return render_template("userClassifiersPage.html")


@app.route("/userclassifierslist/<classToFind>")
def userclassifierslist(classToFind):
    # TODO: Move Classifers to another iframe just add mode than one page can see and test it
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
@app.route("/history")
def history():
    classifierList = db.session.query(Classifiers.name).all()
    classList = db.session.query(Classes.name).distinct(Classes.name).all()
    firstFiveClassList = []
    for i in range(0, 5):
        if len(classList) != 0:
            firstFiveClassList.append(classList.pop(0))
    return render_template("historyPage.html", isAdminOnPage=isAdmin,
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
    return render_template("profilePage.html", isAdminOnPage=isAdmin)


# ----------------------Profile Region

if __name__ == '__main__':
    app.run(threaded=True, debug=True)
    # app.run(host='0.0.0.0',port=5000, threaded=True, debug=True)
