from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
import boto3

class User(UserMixin):
    def __init__(self, username, password_hash=None):
        self.username = username
        self.password_hash = password_hash

    def get_id(self):
        return self.username

    @staticmethod
    def get_user(username):
        table = boto3.resource('dynamodb').Table('users')
        response = table.get_item(Key={'username': username})
        if 'Item' in response:
            return User(username=response['Item']['username'], password_hash=response['Item']['password_hash'])
        return None

    @staticmethod
    def create_user(username, password):
        table = boto3.resource('dynamodb').Table('users')
        password_hash = generate_password_hash(password)
        table.put_item(Item={'username': username, 'password_hash': password_hash})
