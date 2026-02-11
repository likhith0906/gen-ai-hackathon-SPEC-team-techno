import os
import gradio as gr
from groq import Groq
import PyPDF2

client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

def extract_text_from_pdf(pdf_file):
    try:
        pdf_reader = PyPDF2.PdfReader(pdf_file.name)
        text = ""
        for page in pdf_reader.pages:
            extracted = page.extract_text()
            if extracted:
                text += extracted
        return text
    except Exception as e:
        return None

def analyze_resume(pdf_file, resume_type, job_role, company):
    if pdf_file is None:
        return "Please upload a resume PDF file."
    
    resume_text = extract_text_from_pdf(pdf_file)
    if not resume_text:
        return "Failed to extract text from PDF. Please upload a valid resume."
    
    company_context = f"\nTarget Company: {company}" if company.strip() else ""
    
    prompt = f"""You are an expert career advisor analyzing a resume.

Resume Type: {resume_type}
Target Job Role: {job_role}{company_context}

Resume Content:
{resume_text[:3000]}

Analyze this resume and provide output in EXACTLY this format:

CURRENT SKILLS:
- [List 5-7 technical and soft skills found in the resume]

MISSING SKILLS:
- [List 4-6 important skills missing for this role{' at ' + company if company.strip() else ''}]
- Consider the resume type: {'focus on fundamentals and project skills for freshers' if resume_type == 'Fresher' else 'focus on advanced skills and leadership for experienced professionals'}

IMPROVEMENT SUGGESTIONS:
- [3-4 specific, actionable tips to improve this resume]

Be specific and role-aware. Adjust expectations based on resume type."""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Error analyzing resume: {str(e)}"

def extract_missing_skills(analysis_text):
    lines = analysis_text.split('\n')
    skills = []
    capture = False
    
    for line in lines:
        if 'MISSING SKILLS:' in line:
            capture = True
            continue
        if 'IMPROVEMENT SUGGESTIONS:' in line:
            break
        if capture and line.strip().startswith('-'):
            skill = line.strip().lstrip('-').strip()
            if skill:
                skills.append(skill)
    
    return skills

def generate_learning_resources(analysis_text):
    skills = extract_missing_skills(analysis_text)
    
    if not skills:
        return "No missing skills identified."
    
    resources = "### 📚 Learning Resources for Missing Skills\n\n"
    
    for skill in skills:
        clean_skill = skill.split('(')[0].strip()
        youtube_link = f"https://www.youtube.com/results?search_query={clean_skill.replace(' ', '+')}+tutorial"
        course_link = f"https://www.google.com/search?q={clean_skill.replace(' ', '+')}+beginner+course"
        project_link = f"https://www.google.com/search?q={clean_skill.replace(' ', '+')}+project+tutorial"
        
        resources += f"**{clean_skill}**\n"
        resources += f"- [YouTube Tutorials]({youtube_link})\n"
        resources += f"- [Beginner Courses]({course_link})\n"
        resources += f"- [Project-Based Learning]({project_link})\n\n"
    
    return resources

interview_state = {"question_count": 0, "max_questions": 5, "job_role": "", "resume_analyzed": False}

def start_interview(job_role):
    if not interview_state["resume_analyzed"]:
        return "Please analyze your resume first in the Resume Analysis tab."
    
    interview_state["question_count"] = 0
    interview_state["job_role"] = job_role
    
    prompt = f"""You are a professional interviewer conducting an interview for a {job_role} position.

Ask ONE interview question (technical or behavioral). Keep it concise and relevant to the role.
Do not provide any introduction, just ask the question directly."""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.8,
            max_tokens=150
        )
        question = response.choices[0].message.content
        interview_state["question_count"] = 1
        return f"**Question 1:**\n{question}"
    except Exception as e:
        return f"Error: {str(e)}"

def continue_interview(user_answer, job_role):
    if interview_state["question_count"] == 0:
        return "Please click 'Start Interview' first."
    
    if not user_answer.strip():
        return "Please provide an answer to continue."
    
    if interview_state["question_count"] >= interview_state["max_questions"]:
        return "Interview complete! Thank you for your time. Analyze another resume or start a new interview."
    
    prompt = f"""You are interviewing a candidate for {job_role}.

Their answer to the previous question:
"{user_answer}"

First, provide 2-3 sentences of constructive feedback on their answer (max 60 words).
Then ask the next interview question (technical or behavioral).

Format:
Feedback: [your feedback]

Next Question: [your question]"""

    try:
        response = client.chat.completions.create(
            messages=[{"role": "user", "content": prompt}],
            model="llama-3.3-70b-versatile",
            temperature=0.8,
            max_tokens=200
        )
        interview_state["question_count"] += 1
        result = response.choices[0].message.content
        return f"**Question {interview_state['question_count']}:**\n\n{result}"
    except Exception as e:
        return f"Error: {str(e)}"

def process_resume_analysis(pdf_file, resume_type, job_role, company):
    analysis = analyze_resume(pdf_file, resume_type, job_role, company)
    resources = generate_learning_resources(analysis)
    interview_state["resume_analyzed"] = True
    interview_state["job_role"] = job_role
    return analysis, resources

with gr.Blocks(title="VidyaGuide AI Agent") as app:
    gr.Markdown("# 🎯 VidyaGuide AI Agent\n### Intelligent Resume Analyzer, Career Mentor & Interview Trainer")
    
    with gr.Tabs():
        with gr.Tab("📄 Resume Analysis"):
            gr.Markdown("### Upload your resume and get AI-powered insights")
            
            with gr.Row():
                with gr.Column():
                    resume_upload = gr.File(label="Upload Resume (PDF only)", file_types=[".pdf"])
                    resume_type = gr.Dropdown(
                        choices=["Fresher", "Experienced", "Technical", "Non-Technical"],
                        label="Resume Type",
                        value="Fresher"
                    )
                    job_role = gr.Dropdown(
                        choices=[
                            "Software Engineer",
                            "Data Scientist",
                            "Full Stack Developer",
                            "Frontend Developer",
                            "Backend Developer",
                            "DevOps Engineer",
                            "Product Manager",
                            "Business Analyst",
                            "UI/UX Designer",
                            "ML Engineer"
                        ],
                        label="Target Job Role",
                        value="Software Engineer"
                    )
                    company = gr.Textbox(label="Target Company (Optional)", placeholder="e.g., Google, Amazon, Startup")
                    analyze_btn = gr.Button("🔍 Analyze Resume", variant="primary")
                
                with gr.Column():
                    analysis_output = gr.Textbox(label="Resume Analysis", lines=15, max_lines=20)
                    resources_output = gr.Markdown(label="Learning Resources")
            
            analyze_btn.click(
                fn=process_resume_analysis,
                inputs=[resume_upload, resume_type, job_role, company],
                outputs=[analysis_output, resources_output]
            )
        
        with gr.Tab("🎤 Interview Practice"):
            gr.Markdown("### Practice interviews with AI (Resume analysis required first)")
            
            with gr.Row():
                with gr.Column():
                    interview_role = gr.Dropdown(
                        choices=[
                            "Software Engineer",
                            "Data Scientist",
                            "Full Stack Developer",
                            "Frontend Developer",
                            "Backend Developer",
                            "DevOps Engineer",
                            "Product Manager",
                            "Business Analyst",
                            "UI/UX Designer",
                            "ML Engineer"
                        ],
                        label="Interview Role",
                        value="Software Engineer"
                    )
                    start_btn = gr.Button("▶️ Start Interview", variant="primary")
                    user_answer = gr.Textbox(label="Your Answer", lines=4, placeholder="Type your answer here...")
                    submit_btn = gr.Button("📤 Submit Answer")
                
                with gr.Column():
                    interview_output = gr.Textbox(label="Interview", lines=18, max_lines=25)
            
            start_btn.click(
                fn=start_interview,
                inputs=[interview_role],
                outputs=[interview_output]
            )
            
            submit_btn.click(
                fn=continue_interview,
                inputs=[user_answer, interview_role],
                outputs=[interview_output]
            )

app.launch()