from sqlalchemy.orm import Session
from fastapi import UploadFile, HTTPException, status
from app.models.cv import CV
from app.ml.nigerian_parser import nigerian_parser
import PyPDF2
from docx import Document as DocxDocument
import os
from datetime import datetime


class CVService:
    
    UPLOAD_DIR = "/tmp/cv_uploads"  # Change to persistent storage in production
    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5MB
    ALLOWED_EXTENSIONS = ['.pdf', '.docx']
    
    @staticmethod
    def extract_text_from_pdf(file_path: str) -> str:
        """Extract text from PDF"""
        text = ""
        with open(file_path, 'rb') as file:
            pdf_reader = PyPDF2.PdfReader(file)
            for page in pdf_reader.pages:
                text += page.extract_text() + "\n"
        return text.strip()
    
    @staticmethod
    def extract_text_from_docx(file_path: str) -> str:
        """Extract text from DOCX"""
        doc = DocxDocument(file_path)
        text = "\n".join([paragraph.text for paragraph in doc.paragraphs])
        return text.strip()
    
    @staticmethod
    async def upload_cv(db: Session, user_id: int, file: UploadFile) -> CV:
        """Upload and process CV"""
        # Validate file
        if file.size > CVService.MAX_FILE_SIZE:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"File too large. Maximum size is {CVService.MAX_FILE_SIZE / 1024 / 1024}MB"
            )
        
        file_ext = os.path.splitext(file.filename)[1].lower()
        if file_ext not in CVService.ALLOWED_EXTENSIONS:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid file type. Allowed: {', '.join(CVService.ALLOWED_EXTENSIONS)}"
            )
        
        # Create upload directory if not exists
        os.makedirs(CVService.UPLOAD_DIR, exist_ok=True)
        
        # Save file
        file_path = os.path.join(CVService.UPLOAD_DIR, f"{user_id}_{datetime.utcnow().timestamp()}_{file.filename}")
        with open(file_path, "wb") as f:
            content = await file.read()
            f.write(content)
        
        # Extract text
        try:
            if file_ext == '.pdf':
                raw_text = CVService.extract_text_from_pdf(file_path)
            else:  # .docx
                raw_text = CVService.extract_text_from_docx(file_path)
        except Exception as e:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Failed to extract text from file: {str(e)}"
            )
        
        if not raw_text or len(raw_text) < 100:
            os.remove(file_path)
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="CV appears to be empty or too short"
            )
        
        # Parse Nigerian-specific information
        parsed_data = nigerian_parser.parse(raw_text)
        contact = parsed_data.get('contact', {})
        
        # Create CV record
        cv = CV(
            user_id=user_id,
            filename=file.filename,
            file_path=file_path,
            file_size=file.size,
            file_type=file_ext[1:],  # Remove dot
            raw_text=raw_text,
            parsed_data=parsed_data,
            full_name=contact.get('full_name'),
            email=contact.get('email'),
            phone=contact.get('phone'),
            nysc_info=parsed_data.get('nysc_info'),
            siwes_info=parsed_data.get('siwes_info'),
            education=parsed_data.get('education'),
            experience=parsed_data.get('experience'),
            skills=parsed_data.get('skills'),
            processed_at=datetime.utcnow()
        )
        
        db.add(cv)
        db.commit()
        db.refresh(cv)
        
        return cv
    
    @staticmethod
    def get_user_cvs(db: Session, user_id: int, skip: int = 0, limit: int = 100):
        """Get all CVs for a user"""
        return db.query(CV).filter(CV.user_id == user_id).offset(skip).limit(limit).all()
    
    @staticmethod
    def get_cv(db: Session, cv_id: int, user_id: int):
        """Get single CV by ID"""
        cv = db.query(CV).filter(CV.id == cv_id, CV.user_id == user_id).first()
        if not cv:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="CV not found"
            )
        return cv
    
    @staticmethod
    def delete_cv(db: Session, cv_id: int, user_id: int):
        """Delete CV"""
        cv = CVService.get_cv(db, cv_id, user_id)
        
        # Delete file from disk
        if os.path.exists(cv.file_path):
            os.remove(cv.file_path)
        
        db.delete(cv)
        db.commit()
        return True


cv_service = CVService()
