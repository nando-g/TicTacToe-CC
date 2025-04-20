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
from auth import auth
import os, time, sys, argparse

application = Flask(__name__)
application.debug = True
application.secret_key = str(uuid4())

# Flask-Login setup
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

# --- Config and DynamoDB setup ---
parser = argparse.ArgumentParser(description='Run the TicTacToe sample app', prog='application.py')
parser.add_argument('--config', help='Path to the config file containing application settings.')
parser.add_argument('--mode', choices=['local', 'service'], default='service')
parser.add_argument('--endpoint', help='DynamoDB endpoint')
parser.add_argument('--port', type=int)
parser.add_argument('--serverPort', type=int)
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
    if serverPort is None and config.has_option('flask', 'serverPort'):
        serverPort = config.get('flask', 'serverPort')

if 'SERVER_PORT' in os.environ:
    serverPort = int(os.environ['SERVER_PORT'])

if serverPort is None:
    serverPort = 5000

# --- Authentication routes ---
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
    return redirect('/login')

# --- Game routes ---
@application.route('/')
@application.route('/index')
@login_required
def index():
    inviteGames = controller.getGameInvites(current_user.username)
    if inviteGames is None:
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
            flash("Use a valid name (not empty or your own)")
            return redirect("/create")
        if controller.createNewGame(gameId, creator, invitee):
            return redirect("/game="+gameId)
    flash("Something went wrong creating the game.")
    return redirect("/create")

@application.route('/game=<gameId>')
@login_required
def game(gameId):
    item = controller.getGame(gameId)
    if item is None:
        flash("That game does not exist.")
        return redirect("/index")
    boardState = controller.getBoardState(item)
    result = controller.checkForGameResult(boardState, item, current_user.username)
    if result is not None:
        controller.changeGameToFinishedState(item, result, current_user.username)
    game = Game(item)
    status = game.status
    turn = game.turn
    if game.getResult(current_user.username) is None:
        if (turn == game.o):
            turn += " (O)"
        else:
            turn += " (X)"
    gameData = {'gameId': gameId, 'status': game.status, 'turn': game.turn, 'board': boardState}
    gameJson = json.dumps(gameData)
    return render_template("play.html",
                            gameId=gameId,
                            gameJson=gameJson,
                            user=current_user.username,
                            status=status,
                            turn=turn,
                            opponent=game.getOpposingPlayer(current_user.username),
                            result=result,
                            TopLeft=boardState[0],
                            TopMiddle=boardState[1],
                            TopRight=boardState[2],
                            MiddleLeft=boardState[3],
                            MiddleMiddle=boardState[4],
                            MiddleRight=boardState[5],
                            BottomLeft=boardState[6],
                            BottomMiddle=boardState[7],
                            BottomRight=boardState[8])

@application.route('/gameData=<gameId>')
@login_required
def gameData(gameId):
    item = controller.getGame(gameId)
    if item is None:
        return jsonify(error='That game does not exist')
    boardState = controller.getBoardState(item)
    game = Game(item)
    return jsonify(gameId=gameId,
                   status=game.status,
                   turn=game.turn,
                   board=boardState)

@application.route('/accept=<invite>', methods=["POST"])
@login_required
def accept(invite):
    gameId = request.form["response"]
    game = controller.getGame(gameId)
    if game is None:
        flash("That game does not exist anymore.")
        return redirect("/index")
    if not controller.acceptGameInvite(game):
        flash("Error validating the game...")
        return redirect("/index")
    return redirect("/game="+game["GameId"])

@application.route('/reject=<invite>', methods=["POST"])
@login_required
def reject(invite):
    gameId = request.form["response"]
    game = controller.getGame(gameId)
    if game is None:
        flash("That game doesn't exist anymore.")
        return redirect("/index")
    if not controller.rejectGameInvite(game):
        flash("Something went wrong when deleting invite.")
        return redirect("/index")
    return redirect("/index")

@application.route('/select=<gameId>', methods=["POST"])
@login_required
def selectSquare(gameId):
    value = request.form["cell"]
    item = controller.getGame(gameId)
    if item is None:
        flash("This is not a valid game.")
        return redirect("/index")
    if not controller.updateBoardAndTurn(item, value, current_user.username):
        flash("You have selected a square either when \
                it's not your turn, \
                the square is already selected, \
                or the game is not 'In-Progress'.",
                "updateError")
        return redirect("/game="+gameId)
    return redirect("/game="+gameId)

@application.route('/table', methods=["GET", "POST"])
@login_required
def createTable():
    cm.createGamesTable()
    while not controller.checkIfTableIsActive():
        time.sleep(3)
    return redirect('/index')

if __name__ == "__main__":
    if cm:
        application.run(debug=True, port=serverPort, host='0.0.0.0')

