from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import declarative_base, relationship
from datetime import datetime

Base = declarative_base()

class Chat(Base):
    __tablename__ = "chats"

    id = Column(Integer, primary_key=True, autoincrement=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    title = Column(String, nullable=True)

    # one-to-many
    interactions = relationship(
        "Interaction",
        back_populates="chat",
        cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Chat(id={self.id}, created_at={self.created_at})>"

class Interaction(Base):
    __tablename__ = "interactions"

    id = Column(Integer, primary_key=True, autoincrement=True)
    timestamp = Column(DateTime, default=datetime.utcnow)
    user_message = Column(String, nullable=False)
    bot_reply = Column(String, nullable=False)
    risk_level = Column(String, nullable=False)

    # NEW: link to chat
    chat_id = Column(Integer, ForeignKey("chats.id"), index=True, nullable=False)
    chat = relationship("Chat", back_populates="interactions")

    def __repr__(self):
        return f"<Interaction(id={self.id}, chat_id={self.chat_id}, risk_level={self.risk_level}, timestamp={self.timestamp})>"
