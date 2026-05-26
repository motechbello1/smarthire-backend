import re
from typing import Dict, List, Optional


class NigerianCVParser:
    """Extract Nigerian-specific information from CV text"""
    
    # Nigerian universities (sample - expand as needed)
    NIGERIAN_UNIVERSITIES = [
        'university of lagos', 'unilag', 'university of ibadan', 'ui',
        'ahmadu bello university', 'abu', 'university of nigeria', 'unn',
        'obafemi awolowo university', 'oau', 'university of benin', 'uniben',
        'lagos state university', 'lasu', 'covenant university',
        'federal university of technology', 'futa', 'futo', 'futminna'
    ]
    
    def parse(self, text: str) -> Dict:
        """Parse CV and extract Nigerian-specific fields"""
        text_lower = text.lower()
        
        return {
            'nysc_info': self._extract_nysc(text),
            'siwes_info': self._extract_siwes(text),
            'education': self._extract_education(text),
            'experience': self._extract_experience(text),
            'skills': self._extract_skills(text),
            'contact': self._extract_contact(text),
        }
    
    def _extract_nysc(self, text: str) -> Optional[str]:
        """Extract NYSC information"""
        patterns = [
            r'nysc.{0,200}(?:posted|deployed|served|corps member)',
            r'national youth service.{0,200}',
            r'youth corps.{0,100}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0).strip()
        return None
    
    def _extract_siwes(self, text: str) -> Optional[str]:
        """Extract SIWES/Industrial Training information"""
        patterns = [
            r'siwes.{0,200}',
            r'industrial training.{0,200}',
            r'industrial attachment.{0,200}',
            r'student industrial work experience.{0,200}'
        ]
        
        for pattern in patterns:
            match = re.search(pattern, text, re.IGNORECASE | re.DOTALL)
            if match:
                return match.group(0).strip()
        return None
    
    def _extract_education(self, text: str) -> List[Dict]:
        """Extract education history"""
        education = []
        
        # Look for degree patterns
        degree_patterns = [
            r'(b\.?sc\.?|bachelor|bsc|hnd|ond|msc|m\.?sc\.?|master|phd|doctorate).{0,200}',
        ]
        
        for pattern in degree_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE | re.DOTALL)
            for match in matches:
                edu_text = match.group(0).strip()
                
                # Extract year
                year_match = re.search(r'(19|20)\d{2}', edu_text)
                year = year_match.group(0) if year_match else None
                
                # Check for Nigerian university
                is_nigerian = any(uni in edu_text.lower() for uni in self.NIGERIAN_UNIVERSITIES)
                
                education.append({
                    'text': edu_text[:200],  # Limit length
                    'year': year,
                    'is_nigerian_institution': is_nigerian
                })
        
        return education[:5]  # Return top 5
    
    def _extract_experience(self, text: str) -> List[Dict]:
        """Extract work experience"""
        experience = []
        
        # Simple extraction - look for date ranges
        exp_patterns = [
            r'(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4}\s*[-–]\s*(present|current|(jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*\d{4})',
            r'\d{4}\s*[-–]\s*(present|current|\d{4})'
        ]
        
        for pattern in exp_patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)
            for match in matches:
                # Get surrounding context (200 chars before and after)
                start = max(0, match.start() - 200)
                end = min(len(text), match.end() + 200)
                context = text[start:end].strip()
                
                experience.append({
                    'period': match.group(0),
                    'context': context[:300]
                })
        
        return experience[:10]  # Return top 10
    
    def _extract_skills(self, text: str) -> List[str]:
        """Extract skills (basic keyword matching)"""
        # Common technical and soft skills
        skill_keywords = [
            'python', 'javascript', 'java', 'react', 'django', 'sql', 'excel',
            'leadership', 'communication', 'teamwork', 'analysis', 'management',
            'accounting', 'marketing', 'sales', 'data', 'project management'
        ]
        
        text_lower = text.lower()
        found_skills = []
        
        for skill in skill_keywords:
            if skill in text_lower:
                found_skills.append(skill.title())
        
        return list(set(found_skills))[:20]  # Unique, max 20
    
    def _extract_contact(self, text: str) -> Dict:
        """Extract contact information"""
        # Email
        email_match = re.search(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b', text)
        email = email_match.group(0) if email_match else None
        
        # Phone (Nigerian format)
        phone_patterns = [
            r'\+?234\s*\d{10}',
            r'0\d{10}',
            r'\d{11}'
        ]
        phone = None
        for pattern in phone_patterns:
            phone_match = re.search(pattern, text)
            if phone_match:
                phone = phone_match.group(0)
                break
        
        # Name (first line often contains name)
        lines = text.strip().split('\n')
        name = None
        for line in lines[:5]:
            line = line.strip()
            # Likely a name if it's short and has 2-4 words
            words = line.split()
            if 2 <= len(words) <= 4 and len(line) < 50:
                name = line
                break
        
        return {
            'email': email,
            'phone': phone,
            'full_name': name
        }


# Singleton instance
nigerian_parser = NigerianCVParser()
