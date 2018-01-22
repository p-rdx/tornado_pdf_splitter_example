# -*- coding: utf-8 -*-

import os
from sqlalchemy import Column, Integer, String, ForeignKey, BLOB

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from hashlib import md5

BASE_DIR = os.path.dirname(os.path.dirname(__file__))

Base = declarative_base()


class User(Base):
    __tablename__ = 'user'
    pk = Column(Integer, primary_key=True)
    username = Column(String(250), nullable=False)
    password = Column(String(32), nullable=False)


class Files(Base):
    __tablename__ = 'file_storage'
    pk = Column(Integer, primary_key=True)
    storage = Column(BLOB, nullable=False)


class PDFs(Base):
    __tablename__ = 'pdfs'
    pk = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer,
                     ForeignKey('user.pk', onupdate='CASCADE',
                                ondelete='CASCADE'), nullable=False, )
    user = relationship(User)
    storage_id = Column(Integer,
                        ForeignKey('file_storage.pk', onupdate='CASCADE',
                                   ondelete='CASCADE'))
    storage = relationship(Files)
    pages = relationship('Pages', lazy='joined')


class Pages(Base):
    __tablename__ = 'pages'
    pk = Column(Integer, primary_key=True)
    page_number = Column(Integer, nullable=False)
    name = Column(String(250), nullable=False)
    parent_pdf_id = Column(Integer,
                           ForeignKey('pdfs.pk', onupdate='CASCADE',
                                      ondelete='CASCADE'), nullable=False)
    parent_pdf = relationship(PDFs)
    storage_id = Column(Integer,
                        ForeignKey('file_storage.pk', onupdate='CASCADE',
                                   ondelete='CASCADE'), nullable=False)
    storage = relationship(Files)


class DataBase:
    '''
    класс сейчас более или менее безсмысленен
    так как обрабатывает всего один возможный тип дб (sqlite)
    но если понадобиться использовать другие типы,
    то можно будет расширить только его
    не переписывая другую логику
    '''

    def __init__(self, dbname='database'):
        self.dbname = dbname
        self.engine = self.get_engine()
        Session = sessionmaker(bind=self.engine)
        self.session = Session()

    def get_engine(self):
        '''
        на случай если понадобиться выбирать из различных бд
        сейчас обертка для create_engine
        '''
        return create_engine('sqlite:///{}'.format(self.dbname))

    def create_user(self, name, password):
        pwd = md5(password).hexdigest()
        user = User(username=name, password=pwd)
        self.session.add(user)
        try:
            self.session.commit()
        except Exception as e:
            raise e

    def create_database(self):
        '''
        создает базу, создает демо-пользователя
        '''
        engine = self.engine
        Base.metadata.create_all(engine)
        self.create_user(name='demo', password='demo')


if __name__ == '__main__':
    '''
    Тут находится инициализация базы данных
    чтобы разделить с приложением
    '''
    db = DataBase()
    db.create_database()
