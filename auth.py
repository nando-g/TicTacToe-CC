from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_user
from user import User

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = User.get_user(username)
        if user and user.check_password(password):
            login_user(user)
            return redirect(url_for('game.home'))  # Replace with your game route
        flash('Invalid credentials')
    return render_template('login.html')

@auth.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if User.get_user(username):
            flash('Username already exists')
        else:
            User.create_user(username, password)
            return redirect(url_for('auth.login'))
    return render_template('signup.html')
