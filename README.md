
# notioncrypt


A script that encrypts and decrypts your notion pages.

## Setup

- Make sure you have `python` and `pip` properly installed in your system.

    ```shell
    python --version
    pip --version
    ```

- Clone the repo

    ```shell
    git clone https://github.com/Thompsonmina/notioncrypt
    cd notioncrypt
    ```
- Create a virtual env and activate it
    ```
    python -m venv .venv && source .venv/bin/activate
    ```
- Install the dependencies
    ```
    pip install -r requirements.txt
    ```
-Optionally if you have pipenv installed you can create a virtual env and install dependencies in one step
```
    pipenv install
    pipenv shell
```

## Usage

- Go to [notion.so/my-integrations](https://www.notion.so/my-integrations)
to create an integration. Copy the token given by Notion.

> After you create an integration you have to share the pages you want to be able to edit with it

- Generate an encryption key using the command

    ```shell
    python notioncrypt.py generate_key
    ```
> Warning: Do not lose your key, if not you won't be able to decrypt your notion pages

- Copy your Notion token and encryption key into a `.env` file.
```
NOTION_TOKEN=""
ENCRYPT_KEY=""
```
or run the command ` python notioncrypt create_env` to create your `.env` from the shell


- ### Encrypt a page 
```shell
python notioncrypt.py encrypt <notion_page_url>
```

- ### Decrypt a page
```
python notioncrypt.py decrypt <notion_page_url>
```

## Caveats
The notion api is still in beta and is not fully featured yet.

For now you can only encrypt or decrypt:
- pages that have a another page as a parent (top level pages and pages that belong to a database are not supported yet)
- pages that contain only [text-like blocks](https://developers.notion.com/reference/block)
