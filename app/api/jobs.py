# Bring in FastAPI pieces for routes, dependencies, errors, and incoming requests.
from fastapi import APIRouter, Depends, HTTPException, Request
# Bring in the type used for a database session.
from sqlalchemy.orm import Session
# Bring in a way to describe a list of results.
from typing import List
# Bring in the helper that supplies a database connection for each request.
from app.core.database import get_db
# Bring in the expected shapes for new, changed, and returned job data.
from app.schemas.job import JobCreate, JobUpdate, JobResponse
# Bring in the code that does the actual job database work.
from app.services.job_service import job_service
# Bring in the user record type.
from app.models.user import User
# Bring in the helper that checks a sign-in token.
from app.core.security import decode_token

# Group all these endpoints under /jobs and label them Jobs in the API documentation.
router = APIRouter(prefix="/jobs", tags=["Jobs"])


# Start a helper that finds the signed-in user from a request and database session.
def get_current_user(request: Request, db: Session = Depends(get_db)) -> User:
# A note saying what this helper is for.
    """Get current authenticated user"""
# Read the sign-in token from the browser cookie.
    access_token = request.cookies.get("access_token")
# Check whether there was no sign-in token.
    if not access_token:
# If there was none, stop and answer 401, meaning the visitor is not signed in.
        raise HTTPException(status_code=401, detail="Not authenticated")
    
# Check and decode the token into readable data.
    payload = decode_token(access_token)
# Check whether that token was invalid.
    if not payload:
# If invalid, stop with a 401 error.
        raise HTTPException(status_code=401, detail="Invalid token")
    
# Look up the user whose ID is recorded inside the token.
    user = db.query(User).filter(User.id == int(payload.get("sub"))).first()
# Check whether that user was not found.
    if not user:
# If no user exists, stop with a 404 error.
        raise HTTPException(status_code=404, detail="User not found")
    
# Give the verified user record back to the route.
    return user


# Declare a POST route that creates a job; a successful creation returns 201 and JobResponse data.
@router.post("/", response_model=JobResponse, status_code=201)
# Begin the create-job function.
def create_job(
# Accept new job details in the expected shape.
    job_data: JobCreate,
# Require the verified signed-in user before running the function.
    current_user: User = Depends(get_current_user),
# Ask FastAPI to supply the database session.
    db: Session = Depends(get_db)
# Close the function's input list and start its body.
):
# A note saying that this route creates a new job description.
    """Create new job description"""
# Ask the job service to save the new job for this user's ID.
    job = job_service.create_job(db, current_user.id, job_data)
# Send the saved job back to the caller.
    return job


# Declare a GET route that returns a list of jobs.
@router.get("/", response_model=List[JobResponse])
# Begin the list-jobs function.
def list_jobs(
# Let the caller skip a number of results; start with none skipped.
    skip: int = 0,
# Return at most 100 by default.
    limit: int = 100,
# Let the caller ask for only active jobs; default is all jobs.
    active_only: bool = False,
# Require the verified signed-in user.
    current_user: User = Depends(get_current_user),
# Ask for a database session.
    db: Session = Depends(get_db)
# Close the input list and start the function body.
):
# A note saying this route lists this user's jobs.
    """List all jobs for current user"""
# Get this user's jobs, using the skip, limit, and active-only choices.
    jobs = job_service.get_user_jobs(db, current_user.id, skip, limit, active_only)
# Return that list.
    return jobs


# Declare a GET route for one job number.
@router.get("/{job_id}", response_model=JobResponse)
# Begin the get-one-job function.
def get_job(
# Read the job number from the web address.
    job_id: int,
# Require the verified signed-in user.
    current_user: User = Depends(get_current_user),
# Ask for a database session.
    db: Session = Depends(get_db)
# Close the input list and start the function body.
):
# A note saying this route gives details for one job.
    """Get job details"""
# Ask the service to find that job for this user's ID.
    job = job_service.get_job(db, job_id, current_user.id)
# Return the result.
    return job


# Declare a PUT route that changes one job.
@router.put("/{job_id}", response_model=JobResponse)
# Begin the update-job function.
def update_job(
# Read the job number from the web address.
    job_id: int,
# Accept the changes in the expected data shape.
    job_data: JobUpdate,
# Require the verified signed-in user.
    current_user: User = Depends(get_current_user),
# Ask for a database session.
    db: Session = Depends(get_db)
# Close the input list and start the function body.
):
# A note saying this route updates a job.
    """Update job"""
# Ask the service to save the changes to that user's job.
    job = job_service.update_job(db, job_id, current_user.id, job_data)
# Return the updated job.
    return job


# Declare a DELETE route for one job.
@router.delete("/{job_id}")
# Begin the delete-job function.
def delete_job(
# Read the job number from the web address.
    job_id: int,
# Require the verified signed-in user.
    current_user: User = Depends(get_current_user),
# Ask for a database session.
    db: Session = Depends(get_db)
# Close the input list and start the function body.
):
# A note saying this route deletes a job.
    """Delete job"""
# Ask the service to delete that user's job.
    job_service.delete_job(db, job_id, current_user.id)
# Reply with a short success message.
    return {"message": "Job deleted successfully"}
