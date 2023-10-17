> ## Telegram bot "Creating a menu for authorized users" 
> In this project, both frontend and backend have been implemented.
> 
The database was created using Postgres. The following tasks are implemented in the project:

- Authorization: Users of Telegram with specific Telegram IDs can only authorize once. This means there will be no duplicate users with the same Telegram ID in the database.

- Authenticated Users: Once a user is authorized, they have access to the following functions:
  - Viewing the default menu.
  - Creating a custom menu.
  - Viewing the created custom menu.
  
Additionally, there is a database implemented for menus based on the days of the week
