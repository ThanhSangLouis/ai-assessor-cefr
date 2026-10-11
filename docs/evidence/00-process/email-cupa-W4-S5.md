# W4-S5 (SCRUM-52) — Email gửi Cambridge University Press & Assessment

**Trạng thái:** BẢN SOẠN, **CHƯA GỬI**. Người gửi điền các ô trong ngoặc vuông, gửi từ email sinh viên, rồi cập nhật mục "Đã gửi" ở cuối.

- **To:** researchdatasets@cambridge.org
- **Cc:** [email GVHD — điền trước khi gửi]
- **Subject:** Speak & Improve Corpus 2025 — questions on permitted use in a university student project

---

Dear Research Datasets team,

I am Vo Thanh Sang, an undergraduate student in Software Engineering at Ho Chi Minh City University of Technology and Education (HCMUTE), Vietnam. Under the supervision of [GVHD name], our three-person team is building a course project: a tool that *supports* (not replaces) teachers in giving formative feedback on the spoken English of Vietnamese university students at CEFR A2–B2. We obtained the Speak & Improve Corpus 2025 under its research licence and have used it only to train a small linear (Ridge) regression model on 18 acoustic and transcript features. We keep no audio, transcripts or labels in our code repositories, only the fitted coefficients.

Before we go further, we would like to make sure our use stays within the licence. Could you advise on the following three questions?

1. **Use of the trained model for prediction.** May we use the model trained on S&I to produce *provisional* score estimates for our own students' recordings (with their consent) inside the project's demonstration system, where every estimate is labelled as experimental and must be confirmed by a teacher? The system is non-commercial and is used only for the course and its evaluation.

2. **Publishing aggregate statistics.** May we report aggregate results derived from the corpus in our thesis and its presentation — for example cross-validation PCC/RMSE, the number of responses used, model coefficients, and the range of each feature — and may these appear in a project repository that the examiners can read? If publication needs your approval, what is the process?

3. **Computing environment.** May we train and evaluate the model on private notebooks on Google Colab and Kaggle (private datasets, not shared publicly), given that our own machines are not powerful enough?

Until we hear from you, we have removed derived statistics from our team's repository and keep them only in internal documents.

Thank you very much for making the corpus available to students.

Kind regards,
Vo Thanh Sang
Faculty of Information Technology, HCMUTE
[email sinh viên]

---

## Đã gửi

| Ngày gửi | Người gửi | Cc | Trả lời của CUP&A |
| --- | --- | --- | --- |
| [chưa gửi] | | | |

Sau khi gửi: cập nhật bảng trên và Jira SCRUM-52. Không đính kèm dữ liệu, audio hay số liệu suy ra từ corpus.
