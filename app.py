import streamlit as st
import pdfplumber
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import matplotlib.pyplot as plt
import numpy as np
from st_aggrid import AgGrid, GridOptionsBuilder
import mysql.connector
from datetime import datetime
import hashlib

# --- Database Configuration ---
DB_HOST = "localhost"
DB_USER = "root"
DB_PASSWORD = "root"  # Leave it empty if your database has no password
DB_NAME = "rankitright"

def create_connection():
    try:
        mydb = mysql.connector.connect(
            host=DB_HOST,
            user=DB_USER,
            password=DB_PASSWORD,
            database=DB_NAME
        )
        return mydb
    except mysql.connector.Error as err:
        st.error(f"Error connecting to database: {err}")
        return None

# --- User Authentication ---
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()  # Hashing the password

def create_user(username, password, role):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            hashed_password = hash_password(password)
            sql = "INSERT INTO Users (Username, Password, Role) VALUES (%s, %s, %s)"
            cursor.execute(sql, (username, hashed_password, role))
            mydb.commit()
            st.success("User  created successfully!")
            mydb.close()
            return True
        except mysql.connector.Error as err:
            st.error(f"Error creating user: {err}")
            mydb.close()
            return False

def verify_user(username, password):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            hashed_password = hash_password(password)
            sql = "SELECT UserID, Role FROM Users WHERE Username = %s AND Password = %s"
            cursor.execute(sql, (username, hashed_password))
            result = cursor.fetchone()
            mydb.close()
            if result:
                return result[0], result[1]
            else:
                return None, None
        except mysql.connector.Error as err:
            st.error(f"Error verifying user: {err}")
            mydb.close()
            return None, None

def save_hr_ranking_history(username, job_description, resumes, scores):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            resumes_str = ",".join(resumes)
            scores_str = ",".join(map(str, scores))
            sql = "INSERT INTO HRResumeRankingHistory (Username, JobDescription, Resumes, Scores) VALUES (%s, %s, %s, %s)"
            cursor.execute(sql, (username, job_description, resumes_str, scores_str))
            mydb.commit()
            mydb.close()
            return True
        except mysql.connector.Error as err:
            st.error(f"Error saving HR ranking history: {err}")
            mydb.close()
            return False

def get_hr_ranking_history(user_id):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            sql = "SELECT JobDescription, Resumes, Scores, Timestamp FROM HRResumeRankingHistory WHERE Username = %s ORDER BY Timestamp DESC"
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            mydb.close()
            return [(jd, resumes.decode('utf-8'), scores.decode('utf-8'), timestamp) for jd, resumes, scores, timestamp in results]
        except mysql.connector.Error as err:
            st.error(f"Error fetching HR ranking history: {err}")
            mydb.close()
            return []

def save_hr_soft_skill_history(username, videos, scores):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            videos_str = ",".join(videos)
            scores_str = ",".join(map(str, scores))
            sql = "INSERT INTO HRSoftSkillRankingHistory (Username, Videos, Scores) VALUES (%s, %s, %s)"
            cursor.execute(sql, (username, videos_str, scores_str))
            mydb.commit()
            mydb.close()
            return True
        except mysql.connector.Error as err:
            st.error(f"Error saving HR soft skill history: {err}")
            mydb.close()
            return False

def get_hr_soft_skill_history(user_id):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            sql = "SELECT Videos, Scores, Timestamp FROM HRSoftSkillRankingHistory WHERE Username = %s ORDER BY Timestamp DESC"
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            mydb.close()
            return [(videos.decode('utf-8'), scores.decode('utf-8'), timestamp) for videos, scores, timestamp in results]
        except mysql.connector.Error as err:
            st.error(f"Error fetching HR soft skill history: {err}")
            mydb.close()
            return []

def save_hr_feedback(username, feedback):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            sql = "INSERT INTO HRFeedbackHistory (Username, Feedback) VALUES (%s, %s)"
            cursor.execute(sql, (username, feedback))
            mydb.commit()
            mydb.close()
            return True
        except mysql.connector.Error as err:
            st.error(f"Error saving HR feedback: {err}")
            mydb.close()
            return False

def get_hr_feedback_history(user_id):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            sql = "SELECT Feedback, Timestamp FROM HRFeedbackHistory WHERE Username = %s ORDER BY Timestamp DESC"
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            mydb.close()
            return results
        except mysql.connector.Error as err:
            st.error(f"Error fetching HR feedback history: {err}")
            mydb.close()
            return []

def extract_text_from_pdf_hr(file):
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
                else:
                    st.warning(f"No text found on page {page.page_number} of {file.name} (HR).")
    except Exception as e:
        st.error(f"Error reading {file.name} (HR): {e}")
    return text

def rank_resumes_hr(job_description, resumes):
    documents = [job_description] + resumes
    vectorizer = TfidfVectorizer().fit_transform(documents)
    vectors = vectorizer.toarray()
    job_description_vector = vectors[0]
    resume_vectors = vectors[1:]
    cosine_similarities = cosine_similarity([job_description_vector], resume_vectors).flatten()
    return cosine_similarities

def extract_text_from_pdf_student(file):
    text = ""
    try:
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text
                else:
                    st.warning(f"No text found on page {page.page_number} of {file.name} (Student).")
    except Exception as e:
        st.error(f"Error reading {file.name} (Student): {e}")
    return text

def save_student_resume_check_history(user_id, filename, suggestions):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            suggestions_str = ",".join(suggestions)
            sql = "INSERT INTO StudentResumeCheckHistory (Username, Filename, Suggestions) VALUES (%s, %s, %s)"
            cursor.execute(sql, (user_id, filename, suggestions_str))
            mydb.commit()
            mydb.close()
            return True
        except mysql.connector.Error as err:
            st.error(f"Error saving student resume check history: {err}")
            mydb.close()
            return False

def get_student_resume_check_history(user_id):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            sql = "SELECT Filename, Suggestions, Timestamp FROM StudentResumeCheckHistory WHERE Username = %s ORDER BY Timestamp DESC"
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            mydb.close()
            return [(filename, suggestions, timestamp) for filename, suggestions, timestamp in results]
        except mysql.connector.Error as err:
            st.error(f"Error fetching student resume check history: {err}")
            mydb.close()
            return []

def save_student_feedback(username, feedback):
    mydb = create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            sql = "INSERT INTO StudentFeedbackHistory (Username, Feedback) VALUES (%s, %s)"
            cursor.execute(sql, (username, feedback))
            mydb.commit()
            mydb.close()
            return True
        except mysql.connector.Error as err:
            st.error(f"Error saving student feedback: {err}")
            mydb.close()
            return False

def get_student_feedback_history(user_id):
    mydb= create_connection()
    if mydb:
        cursor = mydb.cursor()
        try:
            sql = "SELECT Feedback, Timestamp FROM StudentFeedbackHistory WHERE Username = %s ORDER BY Timestamp DESC"
            cursor.execute(sql, (user_id,))
            results = cursor.fetchall()
            mydb.close()
            return results
        except mysql.connector.Error as err:
            st.error(f"Error fetching student feedback history: {err}")
            mydb.close()
            return []

def evaluate_resume(text):
    suggestions = []

    # Example checks for suggestions
    if len(text) < 500:
        suggestions.append("Consider adding more content to your resume. Aim for at least 500 words.")

    if "skills" not in text.lower():
        suggestions.append("Include a 'Skills' section to highlight your relevant skills.")

    if "experience" not in text.lower():
        suggestions.append("Add an 'Experience' section to showcase your work history.")

    if "education" not in text.lower():
        suggestions.append("Include an 'Education' section to detail your academic background.")

    if len(text.splitlines()) < 5:
        suggestions.append("Your resume is quite short. Consider adding more sections or details.")

    if "objective" not in text.lower() and "summary" not in text.lower():
        suggestions.append("Consider adding an 'Objective' or 'Summary' section to introduce yourself.")

    if "contact" not in text.lower():
        suggestions.append("Make sure to include your contact information at the top of your resume.")

    if any(word in text.lower() for word in ["internship", "intern", "volunteer"]):
        suggestions.append("Highlight any internships or volunteer experiences to showcase your practical skills.")

    if "certification" not in text.lower() and "certificates" not in text.lower():
        suggestions.append("If you have any certifications, consider adding a 'Certifications' section.")

    return suggestions

def student_resume_checker_app(user_id):
    st.subheader("Resume Checker")
    uploaded_file = st.file_uploader("Upload your PDF resume for checking", type=["pdf"], accept_multiple_files=False)

    if uploaded_file:
        with st.spinner("Analyzing your resume..."):
            text = extract_text_from_pdf_student(uploaded_file)
            if text:
                suggestions = evaluate_resume(text)

                st.subheader("Analysis Results")
                if suggestions:
                    st.warning("The following suggestions can help improve your resume:")
                    for i, suggestion in enumerate(suggestions):
                        st.markdown(f"- {i + 1}. {suggestion}")
                else:
                    st.success("Your resume looks well-structured based on our current checks! Keep up the great work.")

                if st.button("Save Check History", key="save_student_history"):
                    if save_student_resume_check_history(user_id, uploaded_file.name, suggestions):
                        st.success("Resume check history saved.")
                    else:
                        st.error("Failed to save resume check history.")
    else:
        st.info("Upload your resume to get improvement suggestions.")

def student_feedback_app(user_id):
    st.subheader("Feedback")
    feedback = st.text_area("Please provide your feedback on the RankItRight platform:", height=150)
    if st.button("Submit Feedback", key="student_submit_feedback", use_container_width=True):
        if feedback:
            if save_student_feedback(user_id, feedback):
                st.success("Thank you for your feedback! We appreciate your input.")
                st.session_state["student_feedback_submitted"] = True
            else:
                st.error("Failed to submit feedback.")
        else:
            st.error("Please enter your feedback before submitting.")

    if "student_feedback_submitted" in st.session_state and st.session_state["student_feedback_submitted"]:
        st.info("Your feedback has been submitted.")
        del st.session_state["student_feedback_submitted"]

def hr_resume_ranking_app(user_id):
    st.subheader("Resume Ranking")
    job_description = st.text_area("Enter the job description for HR", height=200)
    uploaded_files = st.file_uploader("Upload PDF resumes for ranking", type=["pdf"], accept_multiple_files=True)

    resumes_text = []
    if uploaded_files and job_description:
        resume_names = [file.name for file in uploaded_files]
        with st.spinner("Processing resumes..."):
            for file in uploaded_files:
                try:
                    text = extract_text_from_pdf_hr(file)
                    resumes_text.append(text)
                except Exception as e:
                    st.error(f"Error extracting text from {file.name}: {e}")
                    return
    if resumes_text:
        scores = rank_resumes_hr(job_description, resumes_text)
        ranked_indices = scores.argsort()[::-1]
        ranked_scores = scores[ranked_indices]
        ranked_names = [resume_names[i] for i in ranked_indices]

        results_df = pd.DataFrame({
            "Resume": ranked_names,
            "Score": ranked_scores.round(2)
        })

        st.success("Resumes ranked successfully!")
        st.subheader("Ranking Results")
        gb = GridOptionsBuilder.from_dataframe(results_df)
        gb.configure_columns(['Score'], type=['numericColumnFilter', 'customNumericFormat'], precision=2)
        gridOptions = gb.build()
        AgGrid(results_df, gridOptions=gridOptions, height=300, fit_columns_on_grid_load=True)

        fig, ax = plt.subplots()
        ax.pie(ranked_scores, labels=ranked_names, autopct='%1.1f%%', startangle=90)
        ax.axis('equal')
        st.pyplot(fig)
        
        # Add the description below the pie chart
        st.subheader("Understanding Of Results")
        st.write("The pie chart above illustrates the distribution of scores among the ranked resumes. Each slice represents a resume's score relative to the total scores of all resumes. This visual representation helps in understanding how each resume compares to others in terms of alignment with the job description.")

        if st.button("Save Ranking History", key="save_hr_ranking"):
            if save_hr_ranking_history(user_id, job_description, resume_names, ranked_scores.tolist()):
                st.success("Ranking history saved.")
            else:
                st.error("Failed to save ranking history.")

    elif uploaded_files:
        st.warning("Please enter a job description to rank the resumes.")
    elif job_description:
        st.warning("Please upload resumes to perform ranking.")
    else:
        st.info("Upload resumes and enter a job description to see the ranking.")

def hr_soft_skill_ranking_app(user_id):
    st.subheader("Soft Skill Ranking")
    st.info("Upload interview videos for analysis based on communication, tone, and confidence.")
    uploaded_videos = st.file_uploader("Upload Video files for soft skill analysis", type=["mp4", "avi", "mov"], accept_multiple_files=True)

    if uploaded_videos:
        st.info("Note: Soft skill analysis is a complex task and this is a simplified simulation.")
        with st.spinner("Analyzing videos..."):
            video_names = [video.name for video in uploaded_videos]
            communication_scores = np.random.uniform(0.6, 0.95, len(uploaded_videos)).round(2)
            tone_scores = np.random.uniform(0.55, 0.9, len(uploaded_videos)).round(2)
            confidence_scores = np.random.uniform(0.7, 1.0, len(uploaded_videos)).round(2)

            results_df = pd.DataFrame({
                "Video Name": video_names,
                "Communication": communication_scores,
                "Tone": tone_scores,
                "Confidence": confidence_scores
            })
            results_df['Combined Score'] = ((communication_scores + tone_scores + confidence_scores) / 3).round(2)
            ranked_results = results_df.sort_values(by='Combined Score', ascending=False).reset_index(drop=True)
            ranked_results.index += 1

        st.success("Soft skill analysis complete!")
        st.subheader("Soft Skill Ranking Results")
        gb = GridOptionsBuilder.from_dataframe(ranked_results)
        gb.configure_columns(['Communication', 'Tone', 'Confidence', 'Combined Score'],
                             type=['numericColumnFilter', 'customNumericFormat'], precision=2)
        gridOptions = gb.build()
        AgGrid(ranked_results, gridOptions=gridOptions, height=350, fit_columns_on_grid_load=True)

        st.subheader("Detailed Scores")
        st.bar_chart(ranked_results.set_index("Video Name")[["Communication", "Tone", "Confidence"]])
        
        # Add the description below the bar chart
        st.subheader("Understanding Of Results")
        st.write("The bar chart above displays the scores for each video based on three key soft skills: Communication, Tone, and Confidence. Higher scores indicate better performance in these areas, helping to identify candidates with strong interpersonal skills.")

        scores_data = ranked_results[['Video Name', 'Communication', 'Tone', 'Confidence', 'Combined Score']].to_dict('records')

        if st.button("Save Soft Skill History", key="save_hr_soft_skill"):
            if save_hr_soft_skill_history(user_id, video_names, [score['Combined Score'] for score in scores_data]):
                st.success("Soft skill ranking history saved.")
            else:
                st.error("Failed to save soft skill ranking history.")
    else:
        st.info("Upload interview videos to analyze soft skills.")

def hr_feedback_app(user_id):
    st.subheader("Feedback")
    feedback = st.text_area("Please provide your feedback here:", height=150)
    if st.button("Submit Feedback", key="hr_submit_feedback", use_container_width=True):
        if feedback:
            if save_hr_feedback(user_id, feedback):
                st.success("Thank you for your feedback!")
                st.session_state["hr_feedback_submitted"] = True
            else:
                st.error("Failed to submit feedback.")
        else:
            st.error("Please enter your feedback before submitting.")

    if "hr_feedback_submitted" in st.session_state and st.session_state["hr_feedback_submitted"]:
        st.info("Your feedback has been submitted.")
        del st.session_state["hr_feedback_submitted"]

def hr_manage_history_app(user_id):
    st.subheader("Manage History")

    with st.expander("Resume Ranking History", expanded=True):
        ranking_history = get_hr_ranking_history(user_id)
        if ranking_history:
            simplified_history = []
            for jd, resumes_str, scores_str, timestamp in ranking_history:
                resumes = resumes_str.split(',')
                scores = [float(s) for s in scores_str.split(',')] if scores_str else []
                simplified_history.append({
                    "Action": " Resume Ranking",
                    "Job Description": jd[:50] + "...",
                    "Resumes": ", ".join(resumes),
                    "Avg. Score": f"{np.mean(scores).round(2):.2f}" if scores else "N/A",
                    "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })
            if simplified_history:
                history_df = pd.DataFrame(simplified_history)
                history_df.index += 1
                AgGrid(history_df, height=300, fit_columns_on_grid_load=True)
            else:
                st.info("No resume ranking history available.")
        else:
            st.info("No resume ranking history available.")

    with st.expander("Soft Skill Ranking History", expanded=True):
        soft_skill_history = get_hr_soft_skill_history(user_id)
        if soft_skill_history:
            simplified_history = []
            for videos_str, scores_str, timestamp in soft_skill_history:
                videos = videos_str.split(',')
                scores = [float(s) for s in scores_str.split(',')] if scores_str else []
                avg_combined_score = np.mean(scores).round(2) if scores else "N/A"
                simplified_history.append({
                    "Action": "Soft Skill Ranking",
                    "Videos": ", ".join(videos),
                    "Avg. Combined Score": avg_combined_score,
                    "Timestamp": timestamp.strftime("%Y-%m-%d %H:%M:%S")
                })
            if simplified_history:
                history_df = pd.DataFrame(simplified_history)
                history_df.index += 1
                AgGrid(history_df, height=300, fit_columns_on_grid_load=True)
            else:
                st.info("No soft skill ranking history available.")
        else:
            st.info("No soft skill ranking history available.")

    with st.expander("Feedback History", expanded=True):
        feedback_history = get_hr_feedback_history(user_id)
        if feedback_history:
            feedback_df = pd.DataFrame(feedback_history, columns=["Feedback", "Timestamp"])
            feedback_df['Timestamp'] = feedback_df['Timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")
            feedback_df.index += 1
            AgGrid(feedback_df, height=200, fit_columns_on_grid_load=True)
        else:
            st.info("No feedback history available.")

def hr_home_app():
    st.subheader("Welcome to the HR Dashboard")
    st.write("This platform is designed to streamline your hiring process, allowing you to efficiently manage resumes, analyze candidates' soft skills, and provide constructive feedback. Use the navigation menu to explore the various features available to you.")

    st.write("### Key Features")
    st.write("- **Resume Ranking:** Rank multiple resumes based on their relevance to job descriptions using advanced text analysis.")
    st.write("- **Soft Skill Analysis:** Upload interview videos to assess candidates' communication, tone, and confidence levels.")
    st.write("- **Feedback Management:** Provide and track feedback for candidates and the platform itself.")
    st.write("- **History Tracking:** Access your past activities, including resume rankings and soft skill assessments.")

    st.write("### Recent Activity")
    st.write("- **Latest Resume Rankings:** View the most recent rankings performed.")
    st.write("- **Recent Feedback:** Check the latest feedback provided by HR professionals.")

    st.write("### Need Help?")
    st.write("If you have any questions or need assistance then you can access our chatbot.")

def hr_chatbot_app():
    st.subheader("HR Chatbot")
    st.info("Ask your HR-related questions below:")

    user_input = st.text_input("Your question:")

    responses = {
        "How do I rank resumes on RankItRight?": "To rank resumes, navigate to the 'Resume Ranking' section in the sidebar. Enter the job description in the text area provided and upload the PDF resumes you want to rank using the file uploader.",
        "What file types are supported for resume ranking?": "Currently, the 'Resume Ranking' feature only supports PDF files for resume uploads.",
        "Is there a limit to the number of resumes I can upload for ranking?": "While there isn't a strict limit, uploading a very large number of resumes at once might take longer to process. For optimal performance, we recommend uploading in batches if you have hundreds of applications.",
        "How are the resumes ranked? What is the 'Score' based on?": "The resumes are ranked based on the similarity of their content to the job description you provide. The 'Score' represents a cosine similarity score, where a higher score indicates a greater textual similarity between the resume and the job description.",
        "Can I save the resume ranking results?": "Yes, after the resumes are ranked, you'll see a 'Save Ranking History' button. Clicking this will save the job description, the names of the uploaded resumes, and their scores to your history, which you can access in the 'Manage History' section.",
        "How does the 'Soft Skill Ranking' feature work?": "The 'Soft Skill Ranking' section allows you to upload interview video files. The website then performs a simulated analysis based on factors like communication, tone, and confidence, providing a score for each. Please note that this is a simplified simulation for demonstration purposes.",
        "What video file types are supported for soft skill ranking?": "The 'Soft Skill Ranking' feature currently supports MP4, AVI, and MOV video file formats.",
        "What do the 'Communication', 'Tone', and 'Confidence' scores represent?": "These scores are part of a simulated analysis and represent a numerical assessment (on a scale of 0 to 1, approximately) of the candidate's communication clarity, tone during the interview, and perceived confidence levels, based on the uploaded video.",
        "Can I save the soft skill ranking results?": "Yes, after the analysis is complete, a 'Save Soft Skill History' button will appear. Clicking this saves the video file names and their combined scores to your history in the 'Manage History' section.",
        "Where can I provide feedback on the RankItRight platform?": "You can provide feedback by navigating to the 'Feedback' section in the sidebar. There, you'll find a text area where you can enter your comments and suggestions. Click the 'Submit Feedback' button to send it.",
        "Is my feedback anonymous?": "Your feedback is associated with your user account so that we can understand the context. However, your specific identity will be kept confidential when reviewing overall feedback trends.",
        "Where can I see my past resume ranking history?": "You can view your past resume ranking history by clicking on 'Manage History' in the sidebar and then expanding the 'Resume Ranking History' section. This will show you a list of your previous ranking actions, including the job description (partially shown), the resumes you uploaded, their average score, and the timestamp.",
        "Where can I see my past soft skill ranking history?": "Similarly, your past soft skill ranking history can be found in the 'Manage History' section by expanding 'Soft Skill Ranking History'. You'll see the video files you analyzed, their average combined score, and the timestamp.",
        "Can I delete items from my history?": "Currently, the website allows you to view your history, but there is no functionality to delete individual items. This feature might be added in future updates."
    }

    if st.button("Send"):
        if user_input:
            response = responses.get(user_input, "I'm sorry, I don't have an answer for that.")
            st.text_area("Chatbot Response:", value=response, height=150, disabled=True)
        else:
            st.error("Please enter a question.")

def student_manage_history_app(user_id):
    st.subheader("Manage History")

    with st.expander("Resume Check History", expanded=True):
        check_history = get_student_resume_check_history(user_id)
        if check_history:
            history_df = pd.DataFrame(check_history, columns=["Filename", "Suggestions", "Timestamp"])
            history_df['Timestamp'] = history_df['Timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")
            history_df.index += 1
            AgGrid(history_df, height=300, fit_columns_on_grid_load=True)
        else:
            st.info("No resume check history available.")

    with st.expander("Feedback History", expanded=True):
        feedback_history = get_student_feedback_history(user_id)
        if feedback_history:
            feedback_df = pd.DataFrame(feedback_history, columns=["Feedback", "Timestamp"])
            feedback_df['Timestamp'] = feedback_df['Timestamp'].dt.strftime("%Y-%m-%d %H:%M:%S")
            feedback_df.index += 1
            AgGrid(feedback_df, height=200, fit_columns_on_grid_load=True)
        else:
            st.info("No feedback history available.")

def stud_home_app():
    st.subheader("Welcome to the Student Dashboard")
    st.write("This platform is designed to empower you in crafting effective resumes, receiving feedback, and preparing for your career. Use the navigation menu to explore the various features available to you.")

    st.write("### Key Features")
    st.write("- **Resume Checker:** Upload your resume to receive instant feedback and suggestions for improvement.")
    st.write("- **Feedback Submission:** Share your thoughts on the platform and your experience.")
    st.write("- **Manage History:** Track your resume check history and feedback submissions.")
    st.write("- **Career Resources:** Access tips and resources for effective job applications and interviews.")

    st.write("### Recent Activity")
    st.write("- **Latest Resume Checks:** View the most recent feedback received on your resumes.")
    st.write("- **Recent Feedback:** Check the latest feedback you provided on the platform.")

    st.write("### Tips for Effective Job Applications")
    st.write("- **Tailor Your Resume:** Customize your resume for each job application to highlight relevant skills and experiences.")
    st.write("- **Practice Interview Skills:** Prepare for interviews by practicing common questions and researching the company.")
    st.write("- **Network:** Connect with professionals in your field to gain insights and opportunities.")

    st.write("### Need Help?")
    st.write("If you have any questions or need assistance then you can access the chatbot.")

def student_chatbot_app():
    st.subheader("Student Chatbot")
    st.info("Ask questions related to resume building and career advice:")

    user_input = st.text_input("Your question:")

    responses = {
        "How to write a good resume?": "Focus on clear formatting, relevant experience, and quantifiable achievements.",
        "What sections should I include in my resume?": "Essential sections include contact information, summary/objective, experience, education, and skills.",
        "How long should my resume be?": "Ideally, keep your resume to one page, especially if you are early in your career.",
        "Should I include a photo in my resume?": "In most Western countries, it's not necessary and can sometimes lead to bias.",
        "What are action verbs?": "Action verbs are strong verbs that describe your accomplishments and responsibilities (e.g., managed, developed, analyzed).",
        "How to tailor my resume to a job description?": "Identify the key skills and requirements mentioned in the job description and highlight those in your resume.",
        "What is a cover letter?": "A cover letter is a brief introduction to your resume, highlighting your interest in the position and company.",
        "How to prepare for an interview?": "Research the company, practice common interview questions, and prepare thoughtful questions to ask the interviewer.",
    }

    if st.button("Send"):
        if user_input:
            response = responses.get(user_input, "I'm sorry, I don't have information on that. You might find helpful resources on career guidance websites.")
            st.text_area("Chatbot Response:", value=response, height=150, disabled=True)
        else:
            st.error("Please enter a question.")

def student_app(user_id, show_page):
    st.header("Student Dashboard")
    st.sidebar.subheader("Navigation")
    if st.sidebar.button("Home", key="stud_home_btn", use_container_width=True):
        show_page("stud_home")
    if st.sidebar.button("Resume Checker", key="student_resume_checker_btn", use_container_width=True):
        show_page("student_resume_checker")
    if st.sidebar.button("Feedback", key="student_feedback_btn", use_container_width=True):
        show_page("student_feedback")
    if st.sidebar.button("Manage History", key="student_manage_history_btn", use_container_width=True):
        show_page("student_manage_history")
    if st.sidebar.button("Chatbot", key="student_chatbot_btn", use_container_width=True):
        show_page("student_chatbot")
    if st.sidebar.button("Logout", key="student_logout_btn", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state["role"] = None
        st.session_state["user_id"] = None
        st.session_state.student_current_page = None
        st.rerun()

    st.markdown("---")
    if st.session_state.student_current_page == "stud_home":
        stud_home_app()
    if st.session_state.student_current_page == "student_resume_checker":
        student_resume_checker_app(user_id)
    elif st.session_state.student_current_page == "student_feedback":
        student_feedback_app(user_id)
    elif st.session_state.student_current_page == "student_manage_history":
        student_manage_history_app(user_id)
    elif st.session_state.student_current_page == "student_chatbot":
        student_chatbot_app()
    elif st.session_state.student_current_page is None:
        st.info("Welcome to the Student Dashboard! Use the sidebar to navigate.")
        show_page("stud_home")  # Set a default page

def hr_app(user_id, show_page):
    st.header("HR Professional Dashboard")
    st.sidebar.subheader("Navigation")
    if st.sidebar.button("Home", key="hr_home_btn", use_container_width=True):
        show_page("hr_home")
    if st.sidebar.button("Resume Ranking", key="hr_resume_ranking_btn", use_container_width=True):
        show_page("hr_resume_ranking")
    if st.sidebar.button("Soft Skill Ranking", key="hr_soft_skill_ranking_btn", use_container_width=True):
        show_page("hr_soft_skill_ranking")
    if st.sidebar.button("Feedback", key="hr_feedback_btn", use_container_width=True):
        show_page("hr_feedback")
    if st.sidebar.button("Manage History", key="hr_manage_history_btn", use_container_width=True):
        show_page("hr_manage_history")
    if st.sidebar.button("Chatbot", key="hr_chatbot_btn", use_container_width=True):
        show_page("hr_chatbot")
    if st.sidebar.button("Logout", key="hr_logout_btn", use_container_width=True):
        st.session_state["logged_in"] = False
        st.session_state ["role"] = None
        st.session_state["user_id"] = None
        st.session_state.hr_current_page = None
        st.rerun()

    st.markdown("---")

    if st.session_state.hr_current_page == "hr_home":
        hr_home_app()
    elif st.session_state.hr_current_page == "hr_resume_ranking":
        hr_resume_ranking_app(user_id)
    elif st.session_state.hr_current_page == "hr_soft_skill_ranking":
        hr_soft_skill_ranking_app(user_id)
    elif st.session_state.hr_current_page == "hr_feedback":
        hr_feedback_app(user_id)
    elif st.session_state.hr_current_page == "hr_manage_history":
        hr_manage_history_app(user_id)
    elif st.session_state.hr_current_page == "hr_chatbot":
        hr_chatbot_app()
    elif st.session_state.hr_current_page is None:
        st.info("Welcome to the HR Professional Dashboard! Use the sidebar to navigate.")
        show_page("hr_home")  # Set a default page

# --- Main App with Login and Role Selection ---
st.markdown('<style>h1 { font-family: "Times New Roman", Times, serif !important; }</style>', unsafe_allow_html=True)
st.title("RankItRight")

# Custom CSS for gradient buttons
st.markdown(
    """
    <style>
    .stButton>button {
        background: linear-gradient(to right, #007bff, #00bfff); /* Adjust colors as needed */
        color: white;
        border: none;
        border-radius: 5px;
        padding: 10px 20px;
        font-size: 16px;
        cursor: pointer;
        transition: background 0.3s ease;
    }

    .stButton>button:hover {
        background: linear-gradient(to right, #00bfff, #007bff); /* Reverse gradient on hover */
    }
    </style>
    """,
    unsafe_allow_html=True,
)

if "logged_in" not in st.session_state:
    st.session_state["logged_in"] = False
if "role" not in st.session_state:
    st.session_state["role"] = None
if "user_id" not in st.session_state:
    st.session_state["user_id"] = None
if "hr_current_page" not in st.session_state:
    st.session_state["hr_current_page"] = None
if "student_current_page" not in st.session_state:
    st.session_state["student_current_page"] = None

def show_hr_page(page_name):
    st.session_state.hr_current_page = page_name

def show_student_page(page_name):
    st.session_state.student_current_page = page_name

def login_page():
    # Scrolling text HTML
    scrolling_text = """
    <div style="background-color: white; padding: 10px; overflow: auto; white-space: nowrap; width: 100%;">
    <h1 style="display: inline-block; animation: scroll 15s linear infinite; margin: 0; font-size: 1.5em;">
        Rank,Analyze,Succeed...Welcome to RankItRight!
    </h1>
    </div>

    <style>
    @keyframes scroll {
        0% { transform: translateX(100%); }
        100% { transform: translateX(-100%); }
    }
    </style>
    """

    # Display the scrolling text in Streamlit
    st.markdown(scrolling_text, unsafe_allow_html=True)

    st.markdown("""
    RankItRight is designed to streamline the hiring process for HR professionals and empower students in crafting effective resumes.

    For HR Professionals:
    - Effortlessly rank numerous resumes based on job description similarity.
    - Gain insights into candidates' soft skills through video analysis (simulated).
    - Keep track of your ranking history and provide valuable feedback.

    For Students:
    - Receive instant feedback on your resume to identify areas for improvement.
    - Understand key elements recruiters look for in a resume.
    - Track your resume check history and provide feedback on the platform. Get started by creating an account or logging in below:
    """, True)

    col1, col2 = st.columns(2)

    with col1:
        st.markdown(" ### Create Account")
        new_username = st.text_input("New Username")
        new_password = st.text_input("New Password", type="password")
        new_role = st.selectbox("Select your role", ["HR Professional", "Student"], key="new_role")
        if st.button("Create Account", key="create_account_btn", use_container_width=True):
            if new_username and new_password:
                create_user(new_username, new_password, new_role)
            else:
                st.error("Please enter a username and password for the new account.")

    with col2:
        st.markdown("### Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")

        if st.button("Login", use_container_width=True):
            if username and password:
                user_id, role = verify_user(username, password)
                if user_id:
                    st.session_state["logged_in"] = True
                    st.session_state["role"] = role
                    st.session_state["user_id"] = user_id
                    st.success(f"Logged in as {role}!")
                    if role == "HR Professional":
                        st.session_state.hr_current_page = "hr_home"  # Default HR page
                    elif role == "Student":
                        st.session_state.student_current_page = "stud_home"
                    st.rerun()
                else:
                    st.error("Invalid username or password.")
            else:
                st.error("Please enter a username and password.")

if not st.session_state["logged_in"]:
    login_page()
else:
    if st.session_state["role"] == "HR Professional":
        hr_app(st.session_state["user_id"], show_hr_page)
    elif st.session_state["role"] == "Student":
        student_app(st.session_state["user_id"], show_student_page)