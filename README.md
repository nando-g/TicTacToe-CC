In this project we are working to develop a simple Tic-Tac-Toe game application using AWS services. The main components of this project include:

1. **AWS EC2 Instance**: This is where the application will run. We're using an Amazon Linux 2 EC2 instance to host the application.
2. **AWS DynamoDB**: This is used as the backend database to store game state and user data. DynamoDB is a NoSQL database service provided by AWS, which is fully managed and designed for high-performance applications.
3. **Python Application**: The application is written in Python, using Flask for the web framework and Boto for interacting with DynamoDB.

### Project Structure and Components

1. **EC2 Instance Setup**:
   - **Amazon Linux 2**: An Amazon Linux 2 EC2 instance is set up to host the application.
   - **Application Deployment**: The Tic-Tac-Toe application is deployed on this instance.

2. **DynamoDB for Backend Storage**:
   - **Games Table**: A DynamoDB table named `Games` is created to store the state of each game, including information about the players, game status, and board state.
   - **Connection Manager**: A `ConnectionManager` class is used to manage connections to DynamoDB, including setting up the connection and handling queries and updates to the table.

3. **Python Application Components**:
   - **Flask Framework**: Used to handle web requests and render the game interface.
   - **GameController Class**: Manages the game logic, including creating new games, accepting or rejecting game invites, updating the game board, and determining the game result.

### Key Features and Workflow

1. **Create New Game**:
   - A new game can be created by specifying the game ID, creator, and invitee.
   - The game state is initialized and stored in the DynamoDB `Games` table.

2. **Accept/Reject Game Invite**:
   - Players can accept or reject game invites. The game status is updated accordingly in DynamoDB.

3. **Update Game Board**:
   - Players take turns to make moves by updating the board state. Each move is validated and recorded in DynamoDB.
   - The `updateBoardAndTurn` method is used to update the board and switch turns between players.

4. **Check Game Result**:
   - After each move, the game state is checked to determine if there's a win, loss, tie, or if the game is still in progress.
   - The `checkForGameResult` method checks various win conditions and updates the game status in DynamoDB accordingly.

5. **Game State Management**:
   - The game state, including player moves and game status, is stored and managed in DynamoDB.
   - The `GameController` class handles all interactions with DynamoDB to ensure the game state is consistently updated and retrieved.
  
6. **User Authentication**:
   - We first signup/login to enter the game.


```bash
python application.py --config config.ini --mode service --endpoint dynamodb.ap-south-1.amazonaws.com --serverPort 5000
```

