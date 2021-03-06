#!/usr/bin/python
from flask import Flask,render_template, request, flash, Session, url_for, redirect
from flaskext.mysql import MySQL
from flask.ext.login import LoginManager, UserMixin, login_required, login_user, logout_user, current_user
import os

mysql = MySQL()
app = Flask(__name__)
app.config['MYSQL_DATABASE_USER'] = 'admin'
app.config['MYSQL_DATABASE_PASSWORD'] = 'admin'
app.config['MYSQL_DATABASE_DB'] = 'ProjetSGBD'
app.config['MYSQL_DATABASE_HOST'] = 'localhost'
mysql.init_app(app)

app.config['SECRET_KEY'] = 'secret'
app.config['IMAGE_FOLDER'] = 'static/images/recettes'

login_manager = LoginManager()
login_manager.init_app(app)

class User(UserMixin):
	"""docstring for User"""
	def __init__(self, login, id, active=True):
		self.login = login
		self.id = id
		self.active = active

		cursor = mysql.connect().cursor()
		query = "SELECT * FROM Eleve WHERE Id_eleve = " + str(id)
		cursor.execute(query)
		eleve = cursor.fetchone()
		self.lastname = eleve[1]
		self.firstname = eleve[2]
		self.date = eleve[4]
		self.pwd = eleve[5]

	def is_active(self):
		return self.active

	def is_anonymous(self):
		return False

	def is_authenticated(self):
		return True

@login_manager.user_loader
def load_user(id):
	cursor = mysql.connect().cursor()
	query = "SELECT * FROM Eleve WHERE Id_eleve = " + id
	cursor.execute(query)
	eleve = cursor.fetchone()
	userLogin = eleve[3]
	return User(userLogin, id)
		

@app.route("/")
@app.route("/index")
@app.route("/index/<categorie>")
def index(categorie=None):
	cursor = mysql.connect().cursor()
	if (categorie == None):
		query = "SELECT Recette.Id_recette, Nom_recette, Nb_personnes, Budget, Difficulte, COUNT(Date_avis), (avg( Note_qualite ) + avg( Note_justesse ) + avg( Note_respect )) /3 AS Note, Url_image FROM Recette LEFT OUTER JOIN Avis ON Recette.Id_recette = Avis.Id_recette GROUP BY Id_recette, Nom_recette, Nb_personnes, Budget, Url_image"
	else:
		query = "SELECT Recette.Id_recette, Nom_recette, Nb_personnes, Budget, Difficulte, COUNT(Date_avis), (avg( Note_qualite ) + avg( Note_justesse ) + avg( Note_respect )) /3 AS Note, Url_image FROM Recette LEFT OUTER JOIN Avis ON Recette.Id_recette = Avis.Id_recette WHERE Recette.Categorie_recette = '" + categorie + "' GROUP BY Id_recette, Nom_recette, Nb_personnes, Budget, Url_image"
	cursor.execute(query)
	recettes = cursor.fetchall()

	return render_template('index.html', recettes=recettes, categorie=categorie)

@app.route("/recette/<Id_recette>")
def recettes(Id_recette):
	cursor = mysql.connect().cursor()
	query = "SELECT * FROM Recette WHERE Recette.Id_recette = '" + Id_recette + "'"
	cursor.execute(query)
	recette = cursor.fetchone()

	query = "SELECT Login_eleve FROM Recette NATURAL JOIN Eleve WHERE Id_recette = " + Id_recette
	cursor.execute(query)
	auteur = cursor.fetchone()

	query = "SELECT Nom_ingredient, Unite_mesure, Quantite FROM Ingredient,Composer,Recette WHERE Ingredient.Id_ingredient = Composer.Id_ingredient AND Composer.Id_recette = Recette.Id_recette AND Recette.Id_recette = '" + Id_recette + "'"
	cursor.execute(query)
	ingredients = cursor.fetchall()

	query = "SELECT Commentaire, Date_commentaire, Login_eleve FROM Commenter NATURAL JOIN Eleve WHERE Id_recette = '" + Id_recette + "'" 
	cursor.execute(query)
	commentaires = cursor.fetchall()

	query = "SELECT Note_qualite, Note_justesse, Note_respect, Date_avis, Avis_recette, Login_eleve, (Note_qualite+Note_justesse+Note_respect)/3 FROM Avis NATURAL JOIN Eleve WHERE Id_recette = '" + Id_recette + "'"
	cursor.execute(query)
	avis = cursor.fetchall()

	query = "SELECT avg( Note_qualite ), avg( Note_justesse ), avg( Note_respect ), (avg( Note_qualite ) + avg( Note_justesse ) + avg( Note_respect )) /3 FROM Recette LEFT OUTER JOIN Avis ON Avis.Id_recette = '" + Id_recette + "'"
	cursor.execute(query)
	notes = cursor.fetchone()

	query = "SELECT COUNT(Date_avis) FROM Avis WHERE Id_recette = '" + Id_recette + "'"
	cursor.execute(query)
	NbAvis = cursor.fetchone()

	return render_template('recette.html', recette=recette, auteur=auteur, ingredients=ingredients, commentaires=commentaires, avis=avis, notes=notes, nbavis=NbAvis)

@app.route("/recherche")
@app.route("/recherche/")
@app.route("/recherche/",methods=['POST'])
def recherche():
	cursor = mysql.connect().cursor()
	categorie_request = ""
	budget_request = ""
	difficulte_request = ""
	duree_request = ""
	keywords_request = ""
	order_request = ""
	if request.method == 'POST':
		if (request.form['categorie'] != "Tous"):
			categorie_request = "AND Recette.Categorie_recette = '" + request.form['categorie'] + "'"
		if (request.form['minsupBud'] != "Tous" and request.form['budget']!= ""):
			budget_request = "AND (Budget "+ request.form['minsupBud']+ request.form['budget'] +")"
		if (request.form['minsupDif'] != "Tous" and request.form['difficulte']!= ""):
			difficulte_request = "AND (Difficulte "+ request.form['minsupDif']+ request.form['difficulte'] +")"
		if (request.form['minsupDur'] != "Tous" and request.form['duree']!= ""):
			duree_request = "AND (( Temps_preparation + Temps_cuisson) "+ request.form['minsupDur']+ request.form['duree'] +")"
		if (request.form['keywords'] != ""):
			tabkeywords = request.form['keywords'].split()
			keywords_request += " AND ( " 
			for word in tabkeywords:
				keywords_request += "((lower(Nom_recette) LIKE '%" +word+"%') OR ((lower(Nom_ingredient) LIKE '%" +word+"%') AND Composer.Categorie_ingredient = 'principal') OR Recette.Id_eleve IN (SELECT Eleve.Id_eleve	FROM Eleve,Recette WHERE Eleve.Id_eleve = Recette.Id_eleve and (Login_Eleve LIKE '%" + word + "%'))) OR "
			keywords_request += " 0 ) "
		order_request = " ORDER BY "+ request.form['tri'] + " " + request.form['order']
		
		query1 = "SELECT distinct Recette.Id_recette, Nom_recette, Nb_personnes, Budget, Difficulte, Count(Date_avis), (avg( Note_qualite ) + avg( Note_justesse ) + avg( Note_respect )) /3 AS Note, Url_image, Count(*) FROM Recette LEFT OUTER JOIN Avis ON Recette.Id_recette = Avis.Id_recette LEFT OUTER JOIN Commenter ON Recette.Id_recette = Commenter.Id_recette WHERE Recette.Id_recette in ( select Recette.Id_recette FROM Recette LEFT OUTER JOIN Avis ON Recette.Id_recette = Avis.Id_recette LEFT OUTER JOIN Commenter ON Recette.Id_recette = Commenter.Id_recette INNER JOIN Composer INNER JOIN Ingredient WHERE Recette.Id_recette = Composer.Id_recette AND Composer.Id_ingredient = Ingredient.Id_ingredient " + categorie_request + budget_request + difficulte_request + duree_request + keywords_request + " GROUP BY Id_recette) GROUP BY Recette.Id_recette, Nom_recette, Nb_personnes, Budget, Difficulte, Url_image "+ order_request
		cursor.execute(query1)
		recettes = cursor.fetchall()	
		
		query2 = "SELECT count(distinct Nom_recette) FROM Recette LEFT OUTER JOIN Avis ON Recette.Id_recette = Avis.Id_recette LEFT OUTER JOIN Commenter ON Recette.Id_recette = Commenter.Id_recette INNER JOIN Composer INNER JOIN Ingredient where Recette.Id_recette = Composer.Id_recette and Composer.Id_ingredient = Ingredient.Id_ingredient " + categorie_request + budget_request + difficulte_request + duree_request + keywords_request
		cursor.execute(query2)
		nbRecettes = cursor.fetchone()	

			
		return render_template('recherche.html',recettes=recettes,nbRecettes=nbRecettes)
	else:
		return render_template('recherche.html',nbRecettes=None)

@app.route("/users/")
@app.route("/users")
@app.route("/users/",methods=['POST'])
@app.route("/users",methods=['POST'])
def users():
	cursor = mysql.connect().cursor()
	searchrequest = ""
	if request.method == 'POST':
		searchrequest = " WHERE ((lower(Login_eleve) LIKE '%" +request.form['search']+ "%'))"
	query = "SELECT Id_Eleve, Login_eleve, Prenom_eleve, Nom_eleve from Eleve " + searchrequest + " ORDER BY Login_eleve"
	cursor.execute(query)
	users = cursor.fetchall()	
	return render_template('users.html',users=users)

@app.route("/login", methods=['GET', 'POST'])
def login():
	isValidLogin = False
	isValidPassword = False

	cursor = mysql.connect().cursor()
	query = "SELECT * FROM Eleve"
	cursor.execute(query)
	eleves = cursor.fetchall()

	if request.method == "POST" and "username" in request.form:
		login = request.form['username']
		pwd = request.form['password']

		for e in eleves:
			if e[3] == login:
				isValidLogin = True
				if e[5] == pwd:
					isValidPassword = True
					userId = e[0]

		if isValidLogin and isValidPassword:
			validUser = User(login, userId)
			if login_user(validUser):
				return redirect(url_for("index"))
			else:
				return render_template("login.html", error="inconnue")
		elif isValidLogin and not(isValidPassword):
			return render_template("login.html", error="password")
		else:
			return render_template("login.html", error="username")
	return render_template("login.html")

@app.route("/profil/<login>/")
@login_required
def view_profile(login):
	cursor = mysql.connect().cursor()
	query = "SELECT distinct Recette.Id_recette, Categorie_recette, Nom_recette,(Note_qualite + Note_justesse + Note_respect) /3 AS Note FROM Eleve, Recette LEFT OUTER JOIN Avis ON Recette.Id_recette = Avis.Id_recette where Eleve.Id_eleve = Recette.Id_eleve and Eleve.Login_eleve = '" + login +"'" + "group by Recette.Id_recette, Categorie_recette, Nom_recette"
	cursor.execute(query)
	recettes = cursor.fetchall()
	
	queryStat ="SELECT (avg( Note_qualite ) + avg( Note_justesse ) + avg( Note_respect )) /3 AS Note FROM Recette LEFT OUTER JOIN Avis on Recette.Id_recette = Avis.Id_recette INNER JOIN Eleve where Recette.Id_eleve = Eleve.Id_Eleve and Login_Eleve = '" + login +"'"
	cursor.execute(queryStat)
	note = cursor.fetchone()
	
	queryStat ="SELECT avg(Budget) FROM Recette INNER JOIN Eleve where Recette.Id_eleve = Eleve.Id_Eleve and Login_Eleve = '" + login +"'"
	cursor.execute(queryStat)
	budget = cursor.fetchone()
	
	queryStat = "SELECT count(Nom_recette) FROM Recette, Eleve WHERE Recette.Id_eleve= Eleve.id_eleve AND Login_eleve = '" + login +"'"
	cursor.execute(queryStat)
	nbRecettes = cursor.fetchone()
	
	queryStat = "SELECT count(*) FROM Eleve NATURAL JOIN Avis WHERE Login_eleve = '" + login +"'"
	cursor.execute(queryStat)
	nbAvis = cursor.fetchone()
	
	queryStat = "SELECT count(*) FROM Eleve NATURAL JOIN Commenter WHERE Login_eleve = '" + login +"'"
	cursor.execute(queryStat)
	nbComm = cursor.fetchone()
	
	queryStat = "SELECT Nom_eleve, Prenom_eleve, Date_inscription FROM Eleve WHERE Login_eleve = '" + login +"'"	
	cursor.execute(queryStat)
	user = cursor.fetchone()	
	
	return render_template('mesRecettes.html',user=user,login=login,recettes=recettes,budget=budget,note=note,nbRecettes=nbRecettes,nbAvis=nbAvis,nbComm=nbComm)


@app.route("/profil/<login>/edit", methods=['GET', 'POST'])
@login_required
def edit_profil(login):
	if login != current_user.login:
		return redirect(url_for('index'))

	conn = mysql.connect()
	cursor = conn.cursor()
	query = "SELECT * FROM Eleve"
	cursor.execute(query)
	eleves = cursor.fetchall()

	if request.method == "POST":
		firstname = request.form['firstname']
		lastname = request.form['lastname']
		userLogin = request.form['login']
		pwd = request.form['pwd']
		cpwd = request.form['cpwd']

		if userLogin != current_user.login:
			for e in eleves:
				if userLogin == e[3]:
					return render_template('profile.html', error = "Login deja pris !")

		if pwd != cpwd:
			return render_template('profile.html', error = "Mots de passe differents !")

		query = "UPDATE Eleve SET Nom_eleve = %s, Prenom_eleve = %s, Login_eleve = %s, Mot_de_passe = %s WHERE Id_eleve =" + current_user.id
		cursor.execute(query, (lastname, firstname, userLogin, pwd))
		conn.commit()
		return redirect(url_for('index'))

	return render_template('profile.html', error = None)

@app.route('/logout')
@login_required
def logout():
	logout_user()
	return redirect(url_for('index'))

@app.route("/signup", methods=['GET', 'POST'])
def signup():
	conn = mysql.connect()
	cursor = conn.cursor()
	query = "SELECT * FROM Eleve"
	cursor.execute(query)
	eleves = cursor.fetchall()

	if request.method == "POST":
		firstname = request.form['firstname']
		lastname = request.form['lastname']
		login = request.form['login']
		pwd = request.form['pwd']
		cpwd = request.form['cpwd']

		#if login != current_user.login
		for e in eleves:
			if login == e[3]:
				return render_template('profile.html', error = "Login deja pris !")

		if pwd != cpwd:
			return render_template('profile.html', error = "Mots de passe differents !")

		query = "INSERT INTO Eleve (Nom_eleve, Prenom_eleve, Login_eleve, Mot_de_passe) VALUES(%s, %s, %s, %s)"
		cursor.execute(query, (lastname, firstname, login, pwd))
		conn.commit()
		return redirect(url_for('login'))

	return render_template('profile.html', error = None)

@app.route("/nouvelleRecette", methods=['GET', 'POST'])
@login_required
def nouvelleRecette():
	conn = mysql.connect()
	cursor = conn.cursor()
	query = "SELECT * FROM Ingredient"
	cursor.execute(query)
	ingredients = cursor.fetchall()

	if request.method == "POST":
		name = request.form['name']
		budget = request.form['budget']
		difficulty = request.form['difficulty']
		prepTime = request.form['preparationTime']
		cookTime = request.form['cookingTime']
		number = request.form['people']
		recipeIngredients = request.form.getlist('ingredients[]')
		quantites = request.form.getlist('quantites[]')
		unites = request.form.getlist('unites[]')
		principal = request.form.getlist('principal[]')
		instructions = request.form['instructions']
		categorie = request.form['categorie']
		image = request.files['image']
		
		query = "INSERT INTO Recette (Nom_recette, Budget, Difficulte, Temps_preparation, Temps_cuisson, Nb_personnes, Etapes, Categorie_recette, Id_eleve) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)"
		cursor.execute(query, (name, budget, difficulty, prepTime, cookTime, number, instructions, categorie, current_user.id))
		conn.commit()

		query = "SELECT Id_recette FROM Recette ORDER BY Id_recette DESC LIMIT 1"
		cursor.execute(query)
		Id_recette = cursor.fetchone()[0]

		if image:
			imageext = os.path.splitext(image.filename)[1]
			imagename = str(Id_recette) + imageext
			image.save(os.path.join(app.config['IMAGE_FOLDER'], imagename))
			query = "UPDATE Recette SET Url_image = %s WHERE Id_recette = %s"
			cursor.execute(query, (imagename, Id_recette))
			conn.commit()

		ni = len(recipeIngredients)
		for i in range(0,ni):
			ExistingIngredient = False
			for ingr in ingredients:
				if recipeIngredients[i] == ingr[1] and unites[i] == ingr[2]:
					ExistingIngredient = True
					Id_ingredient = ingr[0]
			if not(ExistingIngredient):
				query = "INSERT INTO Ingredient (Nom_ingredient, Unite_mesure) VALUES (LOWER(%s), %s)"
				cursor.execute(query, (recipeIngredients[i], unites[i]))
				conn.commit()

				query = "SELECT Id_ingredient FROM Ingredient ORDER BY Id_ingredient DESC LIMIT 1"
				cursor.execute(query)
				Id_ingredient = cursor.fetchone()[0]

			query = "INSERT INTO Composer (Id_recette, Id_ingredient, Quantite, Categorie_ingredient) VALUES (%s, %s, %s, %s)"
			cursor.execute(query, (Id_recette, Id_ingredient, quantites[i], principal[i]))
			conn.commit()
		return redirect(url_for('recettes', Id_recette = Id_recette))

	return render_template('nouvelleRecette.html', recette = None)

@app.route("/<Id_recette>/edit", methods=['GET', 'POST'])
@login_required
def editRecette(Id_recette):
	conn = mysql.connect()
	cursor = conn.cursor()
	query = "SELECT Id_eleve FROM Recette NATURAL JOIN Eleve WHERE Id_recette = " + Id_recette
	cursor.execute(query)
	auteur = cursor.fetchone()
	if str(auteur[0]) != current_user.id:
		return redirect(url_for('recettes', Id_recette = Id_recette, error = "Ceci n'est pas votre recette !"))

	query = "SELECT * FROM Recette WHERE Id_recette =" + Id_recette
	cursor.execute(query)
	recette = cursor.fetchone()

	query = "SELECT * FROM Ingredient"
	cursor.execute(query)
	ingredients = cursor.fetchall()

	if request.method == "POST":
		
		query = "UPDATE Recette SET Nom_recette = %s, Budget = %s, Difficulte = %s,  Temps_preparation = %s,  Temps_cuisson = %s,  Etapes = %s, Nb_personnes = %s WHERE Id_recette = %s"
		cursor.execute(query, (request.form['name'],request.form['budget'],request.form['difficulte'],request.form['preparationTime'],request.form['cookingTime'],request.form['instructions'],request.form['people'],Id_recette))
		conn.commit()
		return redirect(url_for('recettes', Id_recette = Id_recette, error = "Recette modifiee"))	

		return render_template('nouvelleRecette.html', recette=recette)
		
	return render_template('editRecette.html', recette=recette)

@app.route("/avis/<Id_recette>")
@app.route("/avis/<Id_recette>",methods=['POST'])
@login_required
def ajoutAvis(Id_recette):
	if request.method == 'POST':
		conn = mysql.connect()
		cursor = conn.cursor()
		
		query = "SELECT COUNT(*) FROM Avis WHERE Id_eleve = %s AND Id_recette = %s"
		cursor.execute(query, (current_user.id, Id_recette))
		already = cursor.fetchone()
		
		if already[0] == 1:
			return redirect(url_for('recettes', Id_recette = Id_recette, error = "Vous avez deja un avis"))		
		
		query = "INSERT INTO Avis (Id_eleve,Id_recette,Avis_recette,Note_qualite,Note_justesse,Note_respect) VALUES(%s, %s, %s,%s, %s, %s)"
		cursor.execute(query, (current_user.id, Id_recette, request.form['avis'], request.form['qualite'], request.form['justesse'], request.form['respect']))
		conn.commit()
		return redirect(url_for('recettes', Id_recette = Id_recette, error = "Avis poste"))
	return render_template('ajoutAvis.html',Id_recette=Id_recette)


@app.route("/avis/<Id_recette>/<login>", methods=['GET', 'POST'])
@login_required
def editAvis(Id_recette,login = None):
	
	conn = mysql.connect()
	cursor = conn.cursor()
	query = "SELECT * FROM Avis NATURAL JOIN Eleve WHERE Avis.Id_recette = %s AND Eleve.Login_eleve = %s"
	cursor.execute(query, (Id_recette,login))
	avis = cursor.fetchone()
	
	if login != current_user.login or login== None:
		return redirect(url_for('recettes', Id_recette = Id_recette, error = "Ceci n'est pas votre avis !"))	

	if request.method == "POST":
		avis = request.form['avis']
		justesse = request.form['justesse']
		qualite = request.form['qualite']
		respect = request.form['respect']
		
		query = "UPDATE Avis SET Avis_recette = %s, Note_justesse = %s, Note_qualite = %s, Note_respect = %s WHERE Id_eleve = %s AND Id_recette = %s"
		cursor.execute(query, (avis, justesse, qualite, respect,current_user.id,Id_recette))
		conn.commit()
		return redirect(url_for('recettes', Id_recette = Id_recette, error = "Avis modifie"))	

	return render_template('editAvis.html', Id_recette=Id_recette,avis=avis,error = None)
	

@app.route("/suppression/<login>/<Id_recette>")
@app.route("/suppression/<login>/<Id_recette>",methods=['POST'])
@login_required
def supprRecette(login,Id_recette):
	
	conn = mysql.connect()
	cursor = conn.cursor()
	
	query = "SELECT Login_eleve from Recette natural join Eleve WHERE Recette.Id_recette = %s"
	cursor.execute(query, (Id_recette))
	createur = cursor.fetchone()
	
	if login != current_user.login or createur[0] !=login :
		return redirect(url_for('index', error = "Vous ne pouvez pas supprimer une recette qui ne vous appartient pas."))
	
	if request.method == 'POST':
			
		query = "DELETE FROM Recette WHERE Id_Recette = %s AND Id_eleve = %s"
		cursor.execute(query, (Id_recette, current_user.id))
		conn.commit()
		return redirect(url_for('view_profile', login = login, error = "Recette supprimee"))
		
	return render_template('supprRecette.html',Id_recette=Id_recette)


@app.route("/commentaire/<Id_recette>")
@app.route("/commentaire/<Id_recette>",methods=['POST'])
@login_required
def ajoutCommentaire(Id_recette):
	if request.method == 'POST':
		conn = mysql.connect()
		cursor = conn.cursor()
		query = "INSERT INTO Commenter (Id_eleve,Id_recette,Commentaire) VALUES(%s, %s, %s)"
		cursor.execute(query, (current_user.id, Id_recette, request.form['commentaire']))
		conn.commit()
		return redirect(url_for('recettes', Id_recette = Id_recette, error = "Avis poste"))
	return render_template('ajoutCommentaire.html',Id_recette=Id_recette)

if __name__ == "__main__":
	app.run(debug=True)
