"""
Эндпоинты для управления книгами: список/поиск, получение, добавление,
обновление, удаление. Изменяющие операции (добавить/обновить/удалить)
доступны только Administrator и Librarian.
"""

from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy import or_
from sqlalchemy.orm import Session

from database import get_db
from models import Book, RoleEnum
from schemas import BookCreate, BookUpdate, BookOut, BookListOut
from auth.dependencies import require_role

router = APIRouter()


@router.get("", response_model=BookListOut)
def list_books(
    search: Optional[str] = Query(None, description="Поиск сразу по названию, автору, издателю и ISBN"),
    title: Optional[str] = Query(None, description="Фильтр по названию (частичное совпадение)"),
    author: Optional[str] = Query(None, description="Фильтр по автору"),
    publisher: Optional[str] = Query(None, description="Фильтр по издателю"),
    isbn: Optional[str] = Query(None, description="Фильтр по ISBN"),
    available_only: bool = Query(False, description="Только книги с доступными экземплярами"),
    skip: int = Query(0, ge=0, description="Сколько записей пропустить (пагинация)"),
    limit: int = Query(50, ge=1, le=200, description="Сколько записей вернуть (максимум 200)"),
    db: Session = Depends(get_db),
):
    """Список книг с поиском, фильтрацией и пагинацией."""
    query = db.query(Book)

    if search:
        like = f"%{search}%"
        query = query.filter(
            or_(
                Book.title.ilike(like),
                Book.author.ilike(like),
                Book.publisher.ilike(like),
                Book.isbn.ilike(like),
            )
        )

    if title:
        query = query.filter(Book.title.ilike(f"%{title}%"))
    if author:
        query = query.filter(Book.author.ilike(f"%{author}%"))
    if publisher:
        query = query.filter(Book.publisher.ilike(f"%{publisher}%"))
    if isbn:
        query = query.filter(Book.isbn.ilike(f"%{isbn}%"))
    if available_only:
        query = query.filter(Book.available_copies > 0)

    total = query.count()
    items = query.offset(skip).limit(limit).all()
    return BookListOut(total=total, items=items)


@router.get("/{isbn}", response_model=BookOut)
def get_book(isbn: str, db: Session = Depends(get_db)):
    """Одна книга по ISBN."""
    book = db.query(Book).filter(Book.isbn == isbn).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")
    return book


@router.post(
    "",
    response_model=BookOut,
    status_code=status.HTTP_201_CREATED,
    dependencies=[Depends(require_role(RoleEnum.administrator, RoleEnum.librarian))],
)
def create_book(payload: BookCreate, db: Session = Depends(get_db)):
    """Добавить новую книгу. Доступно: Administrator, Librarian."""
    existing = db.query(Book).filter(Book.isbn == payload.isbn).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Книга с таким ISBN уже существует",
        )

    book = Book(
        isbn=payload.isbn,
        title=payload.title,
        author=payload.author,
        publisher=payload.publisher,
        year=payload.year,
        total_copies=payload.total_copies,
        available_copies=payload.total_copies,
    )
    db.add(book)
    db.commit()
    db.refresh(book)
    return book


@router.put(
    "/{isbn}",
    response_model=BookOut,
    dependencies=[Depends(require_role(RoleEnum.administrator, RoleEnum.librarian))],
)
def update_book(isbn: str, payload: BookUpdate, db: Session = Depends(get_db)):
    """Обновить данные книги (частично). Доступно: Administrator, Librarian."""
    book = db.query(Book).filter(Book.isbn == isbn).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

    update_data = payload.model_dump(exclude_unset=True)

    # Если меняется total_copies — сдвигаем available_copies на ту же разницу,
    # чтобы не "потерять" уже выданные экземпляры и не создать лишние из воздуха.
    if "total_copies" in update_data:
        diff = update_data["total_copies"] - book.total_copies
        book.available_copies = max(0, book.available_copies + diff)

    for field, value in update_data.items():
        setattr(book, field, value)

    db.commit()
    db.refresh(book)
    return book


@router.delete(
    "/{isbn}",
    status_code=status.HTTP_204_NO_CONTENT,
    dependencies=[Depends(require_role(RoleEnum.administrator, RoleEnum.librarian))],
)
def delete_book(isbn: str, db: Session = Depends(get_db)):
    """Удалить книгу. Доступно: Administrator, Librarian."""
    book = db.query(Book).filter(Book.isbn == isbn).first()
    if not book:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Книга не найдена")

    db.delete(book)
    db.commit()
    return None
