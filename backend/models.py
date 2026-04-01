from datetime import datetime
from typing import Optional
from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from backend.database import Base


class Portal(Base):
    __tablename__ = "portals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    url: Mapped[str] = mapped_column(Text, nullable=False)
    enabled: Mapped[bool] = mapped_column(Boolean, default=True)
    requires_auth: Mapped[bool] = mapped_column(Boolean, default=False)
    username: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    password_enc: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    last_scraped_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    scrape_config: Mapped[Optional[str]] = mapped_column(Text, nullable=True)  # JSON
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    tenders: Mapped[list["Tender"]] = relationship("Tender", back_populates="portal")
    scrape_logs: Mapped[list["ScrapeLog"]] = relationship("ScrapeLog", back_populates="portal")


class Keyword(Base):
    __tablename__ = "keywords"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    value: Mapped[str] = mapped_column(String(255), nullable=False, unique=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())


class Tender(Base):
    __tablename__ = "tenders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portal_id: Mapped[int] = mapped_column(Integer, ForeignKey("portals.id"), nullable=False)
    title: Mapped[str] = mapped_column(Text, nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    published_date: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    deadline: Mapped[Optional[str]] = mapped_column(String(20), nullable=True)
    estimated_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    source_url: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    matched_keywords: Mapped[str] = mapped_column(Text, default="[]")  # JSON array
    status: Mapped[str] = mapped_column(String(20), default="new")
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    scraped_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    last_updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)

    portal: Mapped["Portal"] = relationship("Portal", back_populates="tenders")
    proposals: Mapped[list["Proposal"]] = relationship("Proposal", back_populates="tender")


class Template(Base):
    __tablename__ = "templates"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    original_filename: Mapped[str] = mapped_column(String(255), nullable=False)
    blob_url: Mapped[str] = mapped_column(Text, nullable=False)
    file_type: Mapped[str] = mapped_column(String(10), nullable=False)  # pdf | docx
    sha256: Mapped[str] = mapped_column(String(64), nullable=False)
    is_default: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())

    proposals: Mapped[list["Proposal"]] = relationship("Proposal", back_populates="template")


class Proposal(Base):
    __tablename__ = "proposals"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    tender_id: Mapped[int] = mapped_column(Integer, ForeignKey("tenders.id"), nullable=False)
    template_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("templates.id"), nullable=True)
    blob_url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(String(20), default="draft")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=func.now(), onupdate=func.now())

    tender: Mapped["Tender"] = relationship("Tender", back_populates="proposals")
    template: Mapped[Optional["Template"]] = relationship("Template", back_populates="proposals")


class ScrapeLog(Base):
    __tablename__ = "scrape_logs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    portal_id: Mapped[int] = mapped_column(Integer, ForeignKey("portals.id"), nullable=False)
    run_at: Mapped[datetime] = mapped_column(DateTime, default=func.now())
    tenders_found: Mapped[int] = mapped_column(Integer, default=0)
    tenders_new: Mapped[int] = mapped_column(Integer, default=0)
    status: Mapped[str] = mapped_column(String(20), nullable=False)  # success | failed
    error_message: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    portal: Mapped["Portal"] = relationship("Portal", back_populates="scrape_logs")
