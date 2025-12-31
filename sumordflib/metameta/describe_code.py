from sumordflib.metameta import why

class ReasonChain:
    def __init__(self):
        self.reasons = {}

    def __getitem__(self, k):
        return self.reasons[k]

    def __setitem__(self, key, value):
        self.reasons[key] = value

    def get_reason(self, k):
        return self.__getitem__(k)

    def show_all(self):
        return self.reasons


class CodeAdapter:
    def __init__(self, obj, adapted_methods):
        self.obj = obj
        self.__dict__.update(adapted_methods)

    def __str__(self):
        return str(self.obj)



class CodeReasoner:

    def __init__(self):
        self.adapter_registry = {}
        self.chain = ReasonChain()
        self.current_adapter = None

    def related_clause(self, c1, c2):
        return why.BecauseOfData(source=(c1, c2))

    def begin_scope(self, c1, c2):
        return why.BecauseOfData(source=(c1, c2), because="scope_begin")

    def begin_new_language_context(self, context):
        return why.BecauseOfModel(context, subj="begin_new_language_context", pred="owl:sameAs", obj=context)

    def end_new_language_context(self, context):
        return why.BecauseOfModel(context, subj="end_new_language_context", pred="owl:sameAs", obj=context)

    """
    Apply what we have learned by setting a new method to call when we see a given context
    Args:
        :cls: the class to update
        :method: the method to update
        :new_method: the new method we want
        :context: only do it when we see context as the pattern
    """
    def register_context(self, cls, method, new_method, context):
        self.adapter_registry[context] = {
            'class': cls,
            'method': method,
            'new_method': new_method
        }

    def apply_context(self, cls, context):
        if context in self.adapter_registry and self.adapter_registry[context]['class'] == cls:
            # use the adapter pattern to adapt method -> new_method
            adapter_context = self.adapter_registry[context]['new_method']
            name = adapter_context['method'].__name__
            adapter = CodeAdapter(cls, dict([(name, adapter_context['new_method'])]))
            self.current_adapter = adapter
            return adapter
        return None

    def show_code_reasoning(self, code, cls, context):
        if not code:
            return cls
        return code.reasoning(context)

    def show_code(self, code, cls, context):
        if not code:
            return cls
        return code.code(context)

    def show_reasoning_chain(self, chain):
        return self.chain.show_all()




if __name__ == '__main__':
    c = CodeReasoner()
    print(c.related_clause('a=', '10'))
