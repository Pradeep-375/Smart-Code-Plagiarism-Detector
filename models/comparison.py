from datetime import datetime


class Upload:
    def __init__(self, id, user_id, filename, original_filename, file_size,
                 language=None, upload_date=None, file_hash=None):
        self.id = id
        self.user_id = user_id
        self.filename = filename
        self.original_filename = original_filename
        self.file_size = file_size
        self.language = language
        self.upload_date = upload_date or datetime.now()
        self.file_hash = file_hash

    def to_dict(self):
        return {
            'id': self.id,
            'user_id': self.user_id,
            'filename': self.filename,
            'original_filename': self.original_filename,
            'file_size': self.file_size,
            'language': self.language,
            'upload_date': str(self.upload_date),
            'file_hash': self.file_hash
        }


class Comparison:
    def __init__(self, id, file1_id, file2_id, similarity_score=0,
                 token_similarity=0, ast_similarity=0, structure_similarity=0,
                 logic_similarity=0, plagiarism_level='low', compared_by=None,
                 comparison_date=None, report_path=None):
        self.id = id
        self.file1_id = file1_id
        self.file2_id = file2_id
        self.similarity_score = similarity_score
        self.token_similarity = token_similarity
        self.ast_similarity = ast_similarity
        self.structure_similarity = structure_similarity
        self.logic_similarity = logic_similarity
        self.plagiarism_level = plagiarism_level
        self.compared_by = compared_by
        self.comparison_date = comparison_date or datetime.now()
        self.report_path = report_path

    def to_dict(self):
        return {
            'id': self.id,
            'file1_id': self.file1_id,
            'file2_id': self.file2_id,
            'similarity_score': float(self.similarity_score),
            'token_similarity': float(self.token_similarity),
            'ast_similarity': float(self.ast_similarity),
            'structure_similarity': float(self.structure_similarity),
            'logic_similarity': float(self.logic_similarity),
            'plagiarism_level': self.plagiarism_level,
            'compared_by': self.compared_by,
            'comparison_date': str(self.comparison_date),
            'report_path': self.report_path
        }
