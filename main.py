import os
from fastapi import FastAPI, Request, Form, UploadFile, File, Depends, HTTPException, status
from fastapi.responses import RedirectResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlmodel import SQLModel, create_engine, Session, select
from models import User, Recipe, Ingredient, Step, init_db, get_session
from auth import get_current_user, login_user, logout_user, register_user, require_user
from schemas import RecipeCreateForm
from pathlib import Path
from dotenv import load_dotenv
from PIL import Image
import logging

load_dotenv()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

APP_DIR = Path(__file__).parent
UPLOAD_DIR = APP_DIR / 'static' / 'uploads'
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title='Recipe App - Exam MVP')

app.mount('/static', StaticFiles(directory='static'), name='static')
templates = Jinja2Templates(directory='templates')

@app.on_event('startup')
def on_startup():
    init_db()

@app.get('/', response_class=HTMLResponse)
def index(request: Request, q: str = None, type: str = None, ingredient: str = None, session: Session = Depends(get_session)):
    stmt = select(Recipe)
    recipes = session.exec(stmt).all()

    if q:
        recipes = [r for r in recipes if q.lower() in r.title.lower()]
    if type:
        recipes = [r for r in recipes if r.type.lower() == type.lower()]
    if ingredient:
        recipes = [r for r in recipes if any(ingredient.lower() in ing.name.lower() for ing in r.ingredients)]

    return templates.TemplateResponse('index.html', {'request': request, 'recipes': recipes})


@app.get('/register', response_class=HTMLResponse)
def register_get(request: Request):
    return templates.TemplateResponse('register.html', {'request': request})

@app.post('/register')
def register_post(request: Request, username: str = Form(...), password: str = Form(...)):
    user = register_user(username, password)
    if not user:
        return templates.TemplateResponse('register.html', {'request': request, 'error': 'User exists'})
    response = RedirectResponse(url='/', status_code=status.HTTP_302_FOUND)
    login_user(response, user)
    return response

@app.get('/login', response_class=HTMLResponse)
def login_get(request: Request):
    return templates.TemplateResponse('login.html', {'request': request})

@app.post('/login')
def login_post(request: Request, username: str = Form(...), password: str = Form(...)):
    user = require_user(username, password)
    if not user:
        return templates.TemplateResponse('login.html', {'request': request, 'error': 'Invalid credentials'})
    response = RedirectResponse(url='/', status_code=status.HTTP_302_FOUND)
    login_user(response, user)
    return response

@app.get('/logout')
def do_logout():
    response = RedirectResponse(url='/', status_code=status.HTTP_302_FOUND)
    logout_user(response)
    return response

@app.get('/recipes/create', response_class=HTMLResponse)
def create_get(request: Request, current_user: User = Depends(get_current_user)):
    return templates.TemplateResponse('create.html', {'request': request})

@app.post('/recipes/create')
def create_post(
    request: Request, title: str = Form(...), type: str = Form(...),
    min_time: int = Form(0), max_time: int = Form(0),
    ingredients: str = Form(...), steps: str = Form(...),
    image: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    data = RecipeCreateForm(title=title, type=type, min_time=min_time, max_time=max_time, ingredients=ingredients, steps=steps)
    recipe = data.to_model(author_id=current_user.id)
    if image:
        path = UPLOAD_DIR / image.filename
        with open(path, 'wb') as f:
            f.write(image.file.read())
        img = Image.open(path)
        img.thumbnail((1024, 768))
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(path, format="JPEG", optimize=True)
        recipe.image = f'static/uploads/{image.filename}'
    session.add(recipe)
    session.commit()
    session.refresh(recipe)
    return RedirectResponse(f'/', status_code=status.HTTP_302_FOUND)

@app.get('/recipes/{recipe_id}', response_class=HTMLResponse)
def view_recipe(request: Request, recipe_id: int, session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail='Not found')
    return templates.TemplateResponse('recipe.html', {'request': request, 'recipe': recipe})

@app.get('/recipes/{recipe_id}/edit', response_class=HTMLResponse)
def edit_get(request: Request, recipe_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404)
    if recipe.author_id != current_user.id:
        raise HTTPException(status_code=403)
    return templates.TemplateResponse('edit.html', {'request': request, 'recipe': recipe})

@app.post('/recipes/{recipe_id}/edit')
def edit_post(
    request: Request, recipe_id: int, title: str = Form(...), type: str = Form(...),
    min_time: int = Form(0), max_time: int = Form(0),
    ingredients: str = Form(...), steps: str = Form(...),
    image: UploadFile | None = File(None),
    current_user: User = Depends(get_current_user), session: Session = Depends(get_session)
):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404)
    if recipe.author_id != current_user.id:
        raise HTTPException(status_code=403)
    recipe.title = title
    recipe.type = type
    recipe.min_time = min_time
    recipe.max_time = max_time
    # clear old ingredients/steps
    recipe.ingredients = []
    recipe.steps = []
    # reparse
    for line in ingredients.splitlines():
        if not line.strip(): continue
        name, val = line.split(':',1)
        recipe.ingredients.append(Ingredient(name=name.strip(), qty=val.strip()))
    for idx, line in enumerate(steps.splitlines(), start=1):
        if not line.strip(): continue
        recipe.steps.append(Step(order=idx, description=line.strip()))
    if image:
        path = UPLOAD_DIR / image.filename
        with open(path, 'wb') as f:
            f.write(image.file.read())
        img = Image.open(path)
        img.thumbnail((1024,768))
        if img.mode == "RGBA":
            img = img.convert("RGB")
        img.save(path, format='JPEG', optimize=True)
        recipe.image = f'static/uploads/{image.filename}'
    session.add(recipe)
    session.commit()
    return RedirectResponse(f'/recipes/{recipe_id}', status_code=status.HTTP_302_FOUND)

@app.post('/recipes/{recipe_id}/delete')
def delete_recipe(recipe_id: int, current_user: User = Depends(get_current_user), session: Session = Depends(get_session)):
    recipe = session.get(Recipe, recipe_id)
    if not recipe:
        raise HTTPException(status_code=404, detail="Recipe not found")
    if recipe.author_id != current_user.id:
        raise HTTPException(status_code=403, detail="Not allowed to delete this recipe")
    session.delete(recipe)  # каскадне видалення Ingredients/Steps спрацює автоматично
    session.commit()
    return RedirectResponse('/', status_code=status.HTTP_302_FOUND)

@app.get('/health')
def health():
    return {'status': 'ok'}

