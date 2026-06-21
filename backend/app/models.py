"""
SQLAlchemy models for the four required tables:
Books, Users, BorrowTransactions, Reservations.
"""
 
import enum
from sqlalchemy import Column, Integer, String, Date, ForeignKey, Enum
from sqlalchemy.orm import relationship
 
from database import Base
 
 
class RoleEnum(str, enum.Enum):
    administrator = "administrator"
    librarian = "librarian"
    student = "student"
 
 
class BorrowStatus(str, enum.Enum):
    borrowed = "borrowed"
    returned = "returned"
    overdue = "overdue"
 
 
class ReservationStatus(str, enum.Enum):
    pending = "pending"
    fulfilled = "fulfilled"
    cancelled = "cancelled"
 
 
class Book(Base):
    __tablename__ = "books"
 
    isbn = Column(String(20), primary_key=True)
    title = Column(String(500), nullable=False)
    author = Column(String(255))
    publisher = Column(String(255))
    year = Column(Integer, nullable=True)
    total_copies = Column(Integer, default=1)
    available_copies = Column(Integer, default=1)
 
    borrow_transactions = relationship("BorrowTransaction", back_populates="book")
    reservations = relationship("Reservation", back_populates="book")
 
 
class User(Base):
    __tablename__ = "users"
 
    user_id = Column(Integer, primary_key=True, autoincrement=True)
    full_name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False)
    password_hash = Column(String(255), nullable=False)
    role = Column(Enum(RoleEnum), default=RoleEnum.student, nullable=False)
 
    borrow_transactions = relationship("BorrowTransaction", back_populates="user")
    reservations = relationship("Reservation", back_populates="user")
 
 
class BorrowTransaction(Base):
    __tablename__ = "borrow_transactions"
 
    transaction_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    isbn = Column(String(20), ForeignKey("books.isbn"), nullable=False)
    borrow_date = Column(Date, nullable=False)
    due_date = Column(Date, nullable=False)
    return_date = Column(Date, nullable=True)
    status = Column(Enum(BorrowStatus), default=BorrowStatus.borrowed, nullable=False)
 
    user = relationship("User", back_populates="borrow_transactions")
    book = relationship("Book", back_populates="borrow_transactions")
 
 
class Reservation(Base):
    __tablename__ = "reservations"
 
    reservation_id = Column(Integer, primary_key=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.user_id"), nullable=False)
    isbn = Column(String(20), ForeignKey("books.isbn"), nullable=False)
    reservation_date = Column(Date, nullable=False)
    status = Column(Enum(ReservationStatus), default=ReservationStatus.pending, nullable=False)
 
    user = relationship("User", back_populates="reservations")
    book = relationship("Book", back_populates="reservations")