import os,binascii
from flaskblog.models import User, Post
from flask import render_template, url_for, flash, redirect, request, abort
from flaskblog.forms import (RegistrationForm, LoginForm, UpdateAccountForm,
                             PostForm,RequestResetForm, ResetPasswordForm)
from flaskblog import app,db,bcrypt,mail
from flask_login import login_user,current_user,logout_user,login_required
from PIL import Image
from flask_mail import Message



@app.route("/")
@app.route("/home")
def home():
    page=request.args.get('page',1,type=int)
    posts=Post.query.order_by(Post.date_posted.desc()).paginate(page=page,per_page=3)
    return render_template('home.html', posts=posts)


@app.route("/about")
def about():
    return render_template('about.html', title='About')


@app.route("/login", methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user,remember=form.remember.data)
            next_page=request.args.get('next') #this style wont give null pointer exception
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash('Login Unsuccessful. Please check Email and password !!', 'danger')
    return render_template('login.html', title='Login', form=form)


@app.route("/register", methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = RegistrationForm()
    if form.validate_on_submit():
        hashed_password=bcrypt.generate_password_hash(form.password.data)
        user = User(username=form.username.data,email=form.email.data,password=hashed_password)
        db.session.add(user)
        db.session.commit()
        flash('Account Created for {userName} !!'.format(userName=form.username.data), 'success')
        return redirect(url_for('login'))

    return render_template('registration.html', title='Registration', form=form)

@app.route("/logout")
def logout():
    logout_user()
    return redirect(url_for('login'))

def _save_picture(profile_picture):
    random_hex=binascii.b2a_hex(os.urandom(10))
    file_name,file_ext=os.path.splitext(profile_picture.filename)
    profile_picture_name=file_name+random_hex+file_ext
    picture_path=os.path.join(app.root_path,'static/profilePics',profile_picture_name)
    #resizing Image
    outputsize=(125,125)
    i=Image.open(profile_picture)
    i.thumbnail(outputsize)
    i.save(picture_path)
    #with out image resizing
    #profile_picture.save(picture_path)
    return profile_picture_name

@app.route("/account", methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateAccountForm()
    if form.validate_on_submit():
        if form.picture.data:
            profile_picture_name=_save_picture(form.picture.data)
            current_user.image_file= profile_picture_name
        current_user.username = form.username.data
        current_user.email = form.email.data
        db.session.commit()
        flash('Your account has been updated Successfully !!','success')
        return redirect(url_for('account'))
    elif request.method == 'GET':
        form.username.data=current_user.username
        form.email.data=current_user.email

    imageFile=url_for('static',filename='profilePics/'+current_user.image_file)
    return render_template('account.html', title='Account',imageFile=imageFile,form=form)

@app.route("/post/new", methods=['GET', 'POST'])
@login_required
def new_post():
    form = PostForm()
    if form.validate_on_submit():
        post = Post(title=form.title.data, content=form.content.data,author=current_user)
        db.session.add(post)
        db.session.commit()
        flash('Your post has been created !','success')
        return redirect(url_for('home'))
    return render_template('create_post.html', title='New Post',form=form,legend='New Post')


#rout with parameters
@app.route("/post/<int:post_id>", methods=['GET', 'POST'])
def post(post_id):
    post=Post.query.get_or_404(post_id)#will redirect to 404 if post not present
    return render_template('post.html', title=post.title,post=post)

@app.route("/post/<int:post_id>/update", methods=['GET', 'POST'])
@login_required
def post_update(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    form=PostForm()
    if form.validate_on_submit():
        post.title=form.title.data
        post.content=form.content.data
        db.session.commit()
        flash('Post updated Successfully !!','success')
        return redirect(url_for('post',post_id=post.id))
    elif request.method == 'GET':
        form.title.data=post.title
        form.content.data=post.content
    return render_template('create_post.html', title='Update Post', form=form,legend='Update Post')

@app.route("/post/<int:post_id>/delete", methods=['POST'])
@login_required
def post_delete(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
        abort(403)
    db.session.delete(post)
    db.session.commit()
    flash('Your post deleted Successfully !!','success')
    return redirect(url_for('home'))

@app.route("/user/<string:username>")
def user_post(username):
    page=request.args.get('page',1,type=int)
    user=User.query.filter_by(username=username).first_or_404()
    #breaking single line to multiple lines
    posts=Post.query.filter_by(author=user)\
        .order_by(Post.date_posted.desc()).paginate(page=page,per_page=3)
    return render_template('user_posts.html', posts=posts,user=user)

def send_reset_email(user):
    token=user.get_reset_token()
    msg=Message('FlashBlog Password Reset Request',sender='karthik.varagini@imaginea.com'
                ,recipients=[user.email])
    msg.body='''To reset pasword visit following Link: {url}'''.format(url= url_for('reset_token',token=token,_external=True))
    mail.send(msg)

@app.route("/reset_password", methods=['GET', 'POST'])
def reset_request():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form=RequestResetForm()
    if form.validate_on_submit():
        user=User.query.filter_by(email=form.email.data).first()
        send_reset_email(user)
        flash('Email has been sent with Reset Password Link !!','info')
        return redirect(url_for('login'))

    return render_template('reset_request.html', form=form,title='Reset Password')

@app.route("/reset_password/<token>", methods=['GET', 'POST'])
def reset_token(token):
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    user=User.verify_reset_token(token)
    if user is None:
        flash('Invalid or Expired Token !!','warning')
        return redirect(url_for('reset_request'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        hashed_password = bcrypt.generate_password_hash(form.password.data)
        user.password=hashed_password
        db.session.commit()
        flash('Your password has been updated Successfully!!', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form, title='Reset Password')