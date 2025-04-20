from boto.exception import JSONResponseError
from boto.dynamodb2.fields import KeysOnlyIndex, GlobalAllIndex, HashKey, RangeKey
from boto.dynamodb2.layer1 import DynamoDBConnection
from boto.dynamodb2.table import Table

try:
    from urllib.request import urlopen
except ImportError:
    from urllib2 import urlopen
import json

def getDynamoDBConnection(config=None, endpoint=None, port=None, local=False, use_instance_metadata=False):
    params = {
        'is_secure': True
    }

    if config is not None:
        if config.has_option('dynamodb', 'region'):
            params['region'] = config.get('dynamodb', 'region')
        if config.has_option('dynamodb', 'endpoint'):
            params['host'] = config.get('dynamodb', 'endpoint')

    if endpoint is not None:
        params['host'] = endpoint
        if 'region' in params:
            del params['region']

    if 'host' not in params and use_instance_metadata:
        response = urlopen('http://169.254.169.254/latest/dynamic/instance-identity/document').read()
        doc = json.loads(response)
        params['host'] = 'dynamodb.%s.amazonaws.com' % (doc['region'])
        if 'region' in params:
            del params['region']

    return DynamoDBConnection(**params)

def createGamesTable(db):
    try:
        hostStatusDate = GlobalAllIndex("HostId-StatusDate-index",
                                      parts=[HashKey("HostId"), RangeKey("StatusDate")],
                                      throughput={'read': 1, 'write': 1})
        opponentStatusDate = GlobalAllIndex("OpponentId-StatusDate-index",
                                          parts=[HashKey("OpponentId"), RangeKey("StatusDate")],
                                          throughput={'read': 1, 'write': 1})

        gamesTable = Table.create("Games",
                                schema=[HashKey("GameId")],
                                throughput={'read': 1, 'write': 1},
                                global_indexes=[hostStatusDate, opponentStatusDate],
                                connection=db)
    except JSONResponseError:
        gamesTable = Table("Games", connection=db)
    return gamesTable

def createUsersTable(db):
    try:
        usersTable = Table.create("Users",
                                schema=[HashKey("username")],
                                throughput={'read': 1, 'write': 1},
                                connection=db)
    except JSONResponseError:
        usersTable = Table("Users", connection=db)
    return usersTable

if __name__ == "__main__":
    # Initialize connection
    db_conn = getDynamoDBConnection()
    
    # Create tables
    games_table = createGamesTable(db_conn)
    users_table = createUsersTable(db_conn)
    
    print("DynamoDB setup completed successfully!")
    print("Active Tables:", db_conn.list_tables()['TableNames'])
