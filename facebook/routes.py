from flask import render_template, flash, redirect, url_for, request
from facebook import app, db
from facebook.email import send_password_reset_email
from facebook.models import User, Post, Comment, Story, Like, Message
from facebook.forms import RegistrationForm, LoginForm, ResetPasswordRequestForm, ResetPasswordForm, PostForm, EditProfilePhotoForm, EditProfileForm, MessageForm, RecipientList, EditProfileDetailsForm, EmptyForm, EditStoryForm, EditPostForm, CommentForm
from facebook.utilities import save_post_image, save_profile_picture, save_cover_image, save_story_image, save_message_image
from flask_login import login_user, logout_user, current_user, login_required
from werkzeug.urls import url_parse
from datetime import datetime


@app.before_request
def before_request():
    if current_user.is_authenticated:
        current_user.last_seen = datetime.utcnow()
        db.session.commit()


@app.route('/', methods=['GET', 'POST'])
@login_required
def index():
    flash('You are seeing posts from users you are following only')
    form = PostForm()
    user = User.query.filter_by(username=current_user.username).first_or_404()
    stories = Story.query.all()
    page = request.args.get('page', 1, type=int)
    posts = current_user.followed_posts().paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    if form.validate_on_submit():
        post = Post(body=form.post.data, author=current_user)
        if form.post_image.data is not None:
            post_image = save_post_image(form.post_image.data)
            post.post_image = post_image
        db.session.add(post)
        db.session.commit()
        flash('Your post is now live!')
        return redirect(url_for('index'))
    return render_template('index.html', title='Home Page', form=form, posts=posts,
                           next_url=next_url, prev_url=prev_url, user=user, stories=stories)


@app.route('/explore', methods=['GET', 'POST'])
@login_required
def explore():
    flash('You are seeing posts from all users')
    form = EmptyForm()
    users = User.query.all()
    stories = Story.query.all()
    page = request.args.get('page', 1, type=int)
    posts = Post.query.order_by(Post.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('index', page=posts.next_num) \
        if posts.has_next else None
    prev_url = url_for('index', page=posts.prev_num) \
        if posts.has_prev else None
    return render_template('explore.html', title='Explore Page',  next_url=next_url, prev_url=prev_url,  stories=stories, posts=posts, form=form, users=users)


@app.route('/story', methods=['GET', 'POST'])
@login_required
def story():
    form = EditStoryForm()
    if form.validate_on_submit():
        story_image = save_story_image(form.story_image.data)
        story_post = Story(story_image=story_image, author=current_user)
        db.session.add(story_post)
        db.session.commit()
        flash('Your story is now live!')
        return redirect(url_for('index'))
    return render_template('story.html', title='Add Story', form=form)


@app.route('/<username>', methods=['GET', 'POST'])
@login_required
def user(username):
    form = EditProfilePhotoForm()
    emptyform = EmptyForm()
    user = User.query.filter_by(username=username).first_or_404()
    posts = user.posts.order_by(Post.timestamp.desc()).all()
    if form.validate_on_submit():
        cover_image = save_cover_image(form.cover_image.data)
        profile_image = save_profile_picture(form.profile_image.data)
        user.cover_image = cover_image
        user.profile_image = profile_image
        db.session.add(user)
        db.session.commit()
        return redirect(url_for('user', username=username))
    return render_template('profile.html', user=user, posts=posts, title=username, form=form, emptyform=emptyform)


@app.route('/edit/<int:id>', methods=['GET', 'POST'])
@login_required
def edit_post(id):
    post = Post.query.get_or_404(id)
    form = EditPostForm()
    if post.author == current_user and form.validate_on_submit():
        post.body = form.post.data
        post.author= current_user
        if form.post_image.data is not None:
            post_image = save_post_image(form.post_image.data)
            post.post_image = post_image
        db.session.commit()
        flash('The post has been updated.')
        return redirect(url_for('post', id=post.id))
    elif request.method == 'GET':
        form.post.data = post.body
    return render_template('edit_post.html', form=form, title='Edit Post' + str(post.id))


@app.route('/delete_post/<int:id>/', methods=['GET', 'POST'])
def delete_post(id):
    post = Post.query.get_or_404(id)
    db.session.delete(post)
    db.session.commit()
    flash('The post has been deleted.')
    return redirect(url_for('index'))


@app.route('/post/<int:id>', methods=['GET', 'POST'])
@login_required
def post(id):
    post = Post.query.get_or_404(id)
    form = CommentForm()
    page = request.args.get('page', 1, type=int)
    comments = Comment.query.filter_by(post_id=post.id).order_by(Comment.timestamp.desc()).paginate(
        page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('post', page=comments.next_num) \
        if comments.has_next else None
    prev_url = url_for('post', page=comments.prev_num) \
        if comments.has_prev else None
    if form.validate_on_submit():
        comment = Comment(body=form.comment.data,
                          post=post,
                          author=current_user)
        db.session.add(comment)
        db.session.commit()
        flash('Your comment has been published.')
        return redirect(url_for('post', id=post.id))
    return render_template('post.html', form=form, post=post, comments=comments, next_url=next_url, prev_url=prev_url, title='Post' + str(post.id))


@app.route('/<username>/followers', methods=['GET', 'POST'])
@login_required
def followers(username):
    user = User.query.filter_by(username=username).first_or_404()
    folowers = user.followers.all()
    foloweds = user.followed.all()
    return render_template('followers.html', folowers=folowers, foloweds=foloweds, user=user)


@app.route('/edit_profile', methods=['GET', 'POST'])
@login_required
def edit_profile():
    form = EditProfileForm()
    if form.validate_on_submit():
        current_user.f_name = form.f_name.data
        current_user.l_name = form.l_name.data
        current_user.set_username(form.f_name.data, form.l_name.data)
        current_user.about_me = form.about_me.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile'))
    elif request.method == 'GET':
        form.f_name.data = current_user.f_name
        form.l_name.data = current_user.l_name
        form.about_me.data = current_user.about_me
    return render_template('edit_profile.html', title='Edit Profile',
                           form=form)


@app.route('/edit_profile_details', methods=['GET', 'POST'])
@login_required
def edit_profile_details():
    form = EditProfileDetailsForm()
    if form.validate_on_submit():
        current_user.school = form.school.data
        current_user.hometown = form.hometown.data
        current_user.location = form.location.data
        current_user.relationship = form.relationship.data
        db.session.commit()
        flash('Your changes have been saved.')
        return redirect(url_for('edit_profile_details'))
    elif request.method == 'GET':
        form.school.data = current_user.school
        form.hometown.data = current_user.hometown
        form.location.data = current_user.location
        form.relationship.data = current_user.relationship
    return render_template('edit_profile_details.html', title='Edit Profile Details',
                           form=form)


@app.route('/register', methods=['GET', 'POST'])
def register():
    flash('''Here for a demo and don't want to use your real details, you can register using fake info 
    \n or login using: 'email': demo@facebook.com, 'password': 'demo' ''')
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = RegistrationForm()
    if form.validate_on_submit():
        user = User(f_name=form.f_name.data, l_name=form.l_name.data, email=form.email.data.lower(), gender=form.gender.data, dob=form.dob.data)
        user.set_username(form.f_name.data, form.l_name.data)
        user.set_password(form.password.data.lower())
        db.session.add(user)
        db.session.commit()
        flash('Congratulations, you are now a registered user!')
        return redirect(url_for('login'))
    return render_template('register.html', title='Sign Up', form=form)


@app.route('/login', methods=['GET', 'POST'])
def login():

    flash('''Here for a demo and don't want to use your real details, you can register using fake info \n
                or login using: 'email': demo@facebook.com, 'password': 'demo' ''')
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data.lower()).first()
        if user is None or not user.check_password(form.password.data.lower()):
            flash('Invalid username or password')
            return redirect(url_for('login'))
        login_user(user, remember=form.remember_me.data)
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('index')
        return redirect(next_page)
    return render_template('login.html', title='Sign In', form=form)


@app.route('/logout', methods=['GET', 'POST'])
def logout():
    logout_user()
    return redirect(url_for('index'))


@app.route('/follow/<username>', methods=['GET', 'POST'])
@login_required
def follow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(request.referrer)
        if user == current_user:
            flash('You cannot follow yourself!')
            return redirect(request.referrer)
        current_user.follow(user)
        db.session.commit()
        flash('You are following {}!'.format(username))
        return redirect(request.referrer)
    else:
        return redirect(request.referrer)


@app.route('/unfollow/<username>', methods=['POST'])
@login_required
def unfollow(username):
    form = EmptyForm()
    if form.validate_on_submit():
        user = User.query.filter_by(username=username).first()
        if user is None:
            flash('User {} not found.'.format(username))
            return redirect(request.referrer)
        if user == current_user:
            flash('You cannot unfollow yourself!')
            return redirect(request.referrer)
        current_user.unfollow(user)
        db.session.commit()
        flash('You are not following {}.'.format(username))
        return redirect(request.referrer)
    else:
        return redirect(request.referrer)


@app.route('/send_message/<recipient>', methods=['GET', 'POST'])
@login_required
def send_message(recipient):
    user = User.query.filter_by(username=recipient).first_or_404()
    form = MessageForm()
    if form.validate_on_submit():
        msg = Message(author=current_user, recipient=user,
                      body=form.message.data)
        if form.image.data is not None:
            image = save_message_image(form.image.data)
            msg.image = image
        db.session.add(msg)
        db.session.commit()
        flash('Your message has been sent.')
        return redirect(request.referrer)
    return render_template('send_message.html', title='Send Message',
                           form=form, user=user)


@app.route('/messages', methods=['GET', 'POST'])
@login_required
def messages():
    current_user.last_message_read_time = datetime.utcnow()
    db.session.commit()
    page = request.args.get('page', 1, type=int)
    messages = current_user.messages_received.order_by(
        Message.timestamp.desc()).paginate(
            page, app.config['POSTS_PER_PAGE'], False)
    next_url = url_for('messages', page=messages.next_num) \
        if messages.has_next else None
    prev_url = url_for('messages', page=messages.prev_num) \
        if messages.has_prev else None

    return render_template('messages.html', messages=messages,
                           next_url=next_url, prev_url=prev_url, title="Messages")


@app.route('/messaging', methods=['GET', 'POST'])
@login_required
def messaging():
    users = User.query.all()
    form = RecipientList()
    form.recipient.choices = []
    for user in users:
        if current_user == user:
            continue
        form.recipient.choices.append(user.username)
    if form.validate_on_submit():
        return redirect(url_for('send_message', recipient=form.recipient.data))
    return render_template('send_message.html', title='Send Message', form=form)


@app.route('/like/<int:post_id>/<action>', methods=['GET', 'POST'])
@login_required
def like_action(post_id, action):
    post = Post.query.filter_by(id=post_id).first_or_404()
    if action == 'like':
        current_user.like_post(post)
        db.session.commit()
    if action == 'unlike':
        current_user.unlike_post(post)
        db.session.commit()
    return redirect(request.referrer)


@app.route('/users', methods=['GET', 'POST'])
@login_required
def users():
    form=EmptyForm()
    users = User.query.all()
    return render_template('users.html', users=users, form=form, title='users')


@app.route('/reset_password_request', methods=['GET', 'POST'])
def reset_password_request():
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    form = ResetPasswordRequestForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user:
            send_password_reset_email(user)
        flash('Check your email for the instructions to reset your password')
        return redirect(url_for('login'))
    return render_template('reset_password_request.html',
                           title='Reset Password', form=form)


@app.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    if current_user.is_authenticated:
        return redirect(url_for('index'))
    user = User.verify_reset_password_token(token)
    if not user:
        return redirect(url_for('index'))
    form = ResetPasswordForm()
    if form.validate_on_submit():
        user.set_password(form.password.data)
        db.session.commit()
        flash('Your password has been reset.')
        return redirect(url_for('login'))
    return render_template('reset_password.html', form=form)





