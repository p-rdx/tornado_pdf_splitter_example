#-*- coding:utf-8 -*-

import tornado.httpserver
import tornado.ioloop
import tornado.web
import tornado.options
import os.path
from tornado.options import define, options
from hashlib import md5
from database import DataBase, User, Pages, PDFs, Files
from sqlalchemy.orm import subqueryload
from wand.image import Image
from tornado.httpclient import HTTPError


define('port', default=8888, help='run on the given port', type=int)
define('dbname', default='database', help='name for sqlite database', type=str)


db = DataBase(dbname=options.dbname)


def encode_pwd(password):
    '''
    чтобы было удобнее впоследствии делать более сложные методы, чем просто мд5
    '''
    return md5(password).hexdigest()


def pages_generator(blob, resolution=300):
    img = Image(blob=blob, resolution=resolution)
    pages = img.sequence
    for i in xrange(len(pages)):
        img = Image(pages[i])
        img.format = 'png'
        yield img.make_blob()


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        username = self.get_secure_cookie('user')
        user = db.session.query(User).filter(User.username == username).first()
        return user


class DownloadHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self, obj_type, obj_id):
        print obj_type, obj_id
        if obj_type and obj_id:
            key = int(obj_id)
            if obj_type == 'pdf':
                obj = db.session.query(PDFs).\
                    options(subqueryload(PDFs.storage)).get(key)
            elif obj_type == 'png':
                obj = db.session.query(Pages).\
                    options(subqueryload(Pages.storage)).get(key)
            else:
                raise HTTPError(404)
            if obj:
                self.set_header('Content-Type', 'text/csv')
                self.set_header('Content-Disposition', 'attachment; '
                                'filename={}'.format(obj.name))
                self.write(obj.storage.storage)
            else:
                raise HTTPError(404)
        else:
            raise HTTPError(404)


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        pdfs = db.session.query(PDFs).\
            join(PDFs.pages).\
            order_by(PDFs.pk).order_by(Pages.pk).all()
        self.render('index.html', pdfs=pdfs)

    def post(self):
        infile = self.request.files['upload_pdf'][0]
        print type(infile)
        original_fname = infile['filename']
        inp_fname = os.path.splitext(original_fname)[0]
        try:
            fs = Files(storage=infile['body'])
            db.session.add(fs)
            pdf = PDFs(name=original_fname, user=self.current_user, storage=fs)
            db.session.add(pdf)
            pages_data = list()
            pages_blobs = list()
            for i, pg in enumerate(pages_generator(infile['body'])):
                pages_blobs.append(Files(storage=pg))
                page_name = '{}_{}.png'.format(inp_fname, i)
                pages_data.append(Pages(page_number=i, name=page_name,
                                        parent_pdf=pdf,
                                        storage=pages_blobs[-1]))
            db.session.add_all(pages_blobs)
            db.session.add_all(pages_data)
            db.session.commit()
        except Exception as e:
            print(e)
            raise HTTPError(500)
        pdfs = db.session.query(PDFs).join(PDFs.pages).all()
        self.render('index.html', pdfs=pdfs)


class RegisterHandler(BaseHandler):
    def get(self):
        self.render('register.html', error=False)

    def post(self):
        get_name = tornado.escape.xhtml_escape(self.get_argument('username'))
        pwd1 = tornado.escape.xhtml_escape(self.get_argument('password1'))
        pwd2 = tornado.escape.xhtml_escape(self.get_argument('password2'))
        existed = db.session.query(User).\
            filter(User.username == get_name).first()
        if existed:
            self.render('register.html', error=True,
                        err_text='User with this username already exists')
        if pwd1 == pwd2:
            user = User(username=get_name, password=encode_pwd(pwd1))
            db.session.add(user)
            try:
                db.session.commit()
            except Exception as e:
                print(e)
                raise HTTPError(500)
            self.set_secure_cookie('user', user.username)
            self.redirect(self.reverse_url('main'))
        else:
            self.render('register.html', error=True,
                        err_text='Passwords should be equal')


class LoginHandler(BaseHandler):
    def get(self):
        self.render('login.html', error=False)

    def post(self):
        get_name = tornado.escape.xhtml_escape(self.get_argument('username'))
        get_pwd = tornado.escape.xhtml_escape(self.get_argument('password'))

        user = db.session.query(User).filter(User.username == get_name).first()
        if user and user.password == md5(get_pwd).hexdigest():
            self.set_secure_cookie('user', user.username)
            self.redirect(self.reverse_url('main'))
        else:
            self.render('login.html', error=True)


class LogoutHandler(BaseHandler):
    def get(self):
        self.clear_cookie('user')
        self.redirect(self.get_argument('next', self.reverse_url('main')))


class Application(tornado.web.Application):
    def __init__(self):
        base_dir = os.path.dirname(__file__)
        settings = {
            'cookie_secret': 'bZJc2sWbQLKos6GkHn/VB9oXwQt8S0R0kRvJ5/xJ89E=',
            'login_url': '/login',
            'template_path': os.path.join(base_dir, 'templates'),
            'static_path': os.path.join(base_dir, 'static'),
            'debug': True,
            'xsrf_cookies': True,
        }
        tornado.web.Application.__init__(self, [
            tornado.web.url(r'/', MainHandler, name='main'),
            tornado.web.url(r'/login', LoginHandler, name='login'),
            tornado.web.url(r'/logout', LogoutHandler, name='logout'),
            tornado.web.url(r'/download/([pdfng]{3})/(\d+)',
                            DownloadHandler, name='download'),
            tornado.web.url(r'/register', RegisterHandler, name='register'),
        ], **settings)


def main():
    tornado.options.parse_command_line()
    Application().listen(options.port)
    tornado.ioloop.IOLoop.instance().start()


if __name__ == '__main__':
    main()
