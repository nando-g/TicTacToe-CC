#!flask/bin/python
from flask_login import LoginManager, UserMixin, login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from boto.dynamodb2.table import Table
from dynamodb.connectionManager import ConnectionManager
from dynamodb.gameController import GameController
from models.game import Game
from uuid import uuid4
from flask import Flask, render_template, request, session, flash, redirect, jsonify, json
from configparser import ConfigParser
import os, time, sys, argparse

application = Flask(__name__)
application.debug = True
application.secret_key = str(uuid4())

# Initialize Flask-Login
login_manager = LoginManager()
login_manager.init_app(application)
login_manager.login_view = 'login'

class User(UserMixin):
    def __init__(self, username, password_hash=None):
        self.username = username
        self.password_hash = password_hash

    def get_id(self):
        return self.username

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    @staticmethod
    def get(username):
        try:
            users_table = Table("Users")
            user_item = users_table.get_item(username=username)
            return User(
                username=user_item['username'],
                password_hash=user_item['password_hash']
            )
        except Exception:
            return None

    @staticmethod
    def create(username, password):
        users_table = Table("Users")
        users_table.put_item(data={
            'username': username,
            'password_hash': generate_password_hash(password)
        })

@login_manager.user_loader
def load_user(username):
    return User.get(username)

# Original connection setup remains unchanged
cm = None
parser = argparse.ArgumentParser(description='Run the TicTacToe sample app', prog='application.py')
parser.add_argument('--config', help='Path to the config file containing application settings. Cannot be used if the CONFIG_FILE environment variable is set instead')
parser.add_argument('--mode', help='Whether to connect to a DynamoDB service endpoint, or to connect to DynamoDB Local. In local mode, no other configuration ' \
                    'is required. In service mode, AWS credentials and endpoint information must be provided either on the command-line or through the config file.',
                    choices=['local', 'service'], default='service')
parser.add_argument('--endpoint', help='An endpoint to connect to (the host name - without the http/https and without the port). ' \
                    'When using DynamoDB Local, defaults to localhost. If the USE_EC2_INSTANCE_METADATA environment variable is set, reads the instance ' \
                    'region using the EC2 instance metadata service, and contacts DynamoDB in that region.')
parser.add_argument('--port', help='The port of DynamoDB Local endpoint to connect to.  Defaults to 8000', type=int)
parser.add_argument('--serverPort', help='The port for this Flask web server to listen on.  Defaults to 5000 or whatever is in the config file. If the SERVER_PORT ' \
                    'environment variable is set, uses that instead.', type=int)
args = parser.parse_args()

configFile = args.config
config = None
if 'CONFIG_FILE' in os.environ:
    if configFile is not None:
        raise Exception('Cannot specify --config when setting the CONFIG_FILE environment variable')
    configFile = os.environ['CONFIG_FILE']
if configFile is not None:
    config = ConfigParser()
    config.read(configFile)

use_instance_metadata = ""
if 'USE_EC2_INSTANCE_METADATA' in os.environ:
    use_instance_metadata = os.environ['USE_EC2_INSTANCE_METADATA']

cm = ConnectionManager(mode=args.mode, config=config, endpoint=args.endpoint, port=args.port, use_instance_metadata=use_instance_metadata)
controller = GameController(cm)

serverPort = args.serverPort
if config is not None:
    if config.has_option('flask', 'secret_key'):
        application.secret_key = config.get('flask', 'secret_key')
    if serverPort is None:
        if config.has_option('flask', 'serverPort'):
            serverPort = config.get('flask', 'serverPort')

if 'SERVER_PORT' in os.environ:
    serverPort = int(os.environ['SERVER_PORT'])

if serverPort is None:
    serverPort = 5000

# Authentication routes
@application.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect('/index')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.get(username)
        
        if user and user.check_password(password):
            login_user(user)
            return redirect('/index')
        flash('Invalid username or password')
    return render_template('login.html')

@application.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect('/index')
    
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        if User.get(username):
            flash('Username already exists')
        else:
            User.create(username, password)
            flash('Account created successfully! Please login.')
            return redirect('/login')
    
    return render_template('signup.html')

@application.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect('/index')

# Modified existing routes
@application.route('/')
@application.route('/index', methods=["GET", "POST"])
@login_required
def index():
    inviteGames = controller.getGameInvites(current_user.username)
    if inviteGames == None:
        flash("Table has not been created yet, please follow this link to create table.")
        return render_template("table.html", user="")
    
    inviteGames = [Game(inviteGame) for inviteGame in inviteGames]
    inProgressGames = controller.getGamesWithStatus(current_user.username, "IN_PROGRESS")
    inProgressGames = [Game(inProgressGame) for inProgressGame in inProgressGames]
    finishedGames = controller.getGamesWithStatus(current_user.username, "FINISHED")
    fs = [Game(finishedGame) for finishedGame in finishedGames]

    return render_template("index.html",
            user=current_user.username,
            invites=inviteGames,
            inprogress=inProgressGames,
            finished=fs)

@application.route('/create')
@login_required
def create():
    return render_template("create.html", user=current_user.username)

@application.route('/play', methods=["POST"])
@login_required
def play():
    form = request.form
    if form:
        creator = current_user.username
        gameId = str(uuid4())
        invitee = form["invitee"].strip()

        if not invitee or creator == invitee:
            flash("Use valid a name (not empty or your name)")
            return redirect("/create")

        if controller.createNewGame(gameId, creator, invitee):
            return redirect("/game="+gameId)

    flash("Something went wrong creating the game.")
    return redirect("/create")

# Other game routes remain similar but with @login_required decorator
# ...

@application.route('/table', methods=["GET", "POST"])
@login_required
def createTable():
    cm.createGamesTable()
    while controller.checkIfTableIsActive() == False:
        time.sleep(3)
    return redirect('/index')

if __name__ == "__main__":
    if cm:
        application.run(debug = True, port=serverPort, host='0.0.0.0')
