from sumordflib.metameta import why

class CodeReasoner:

    def related_clause(self, c1, c2):
        return why.BecauseOfData(source=(c1, c2))

    def begin_scope(self, c1, c2):
        return why.BecauseOfData(source=(c1, c2), because="scope_begin")

    def begin_new_language_context(self, context):
        return why.BecauseOfModel(context, subj="begin_new_language_context", pred="owl:sameAs", obj=context)

    def end_new_language_context(self, context):
        return why.BecauseOfModel(context, subj="end_new_language_context", pred="owl:sameAs", obj=context)





if __name__ == '__main__':
    c = CodeReasoner()

    print(c.related_clause('a=', '10'))
