from flask.views import MethodView, MethodViewType

from wish_flask.log.meta import LoggingMixinMeta, LoggingMixin


class WishMethodMeta(MethodViewType, LoggingMixinMeta):
    pass


class WishMethodView(MethodView, LoggingMixin, metaclass=WishMethodMeta):
    pass


class ViewFilter(object):
    def __init__(self, name=None):
        self.name = name or self.__class__.__name__

    @classmethod
    def process_next(cls, next_filter_node, view_func, fargs, fkwargs):
        if next_filter_node:
            return next_filter_node.process(view_func, fargs, fkwargs)
        return view_func(*fargs, **fkwargs)

    def process(self, next_filter_node, view_func, fargs, fkwargs):
        return self.process_next(next_filter_node, view_func, fargs, fkwargs)


class ViewFilterNode(object):
    def __init__(self, view_filter):
        self.view_filter = view_filter
        self.next = None

    @property
    def name(self):
        return self.view_filter.name if self.view_filter else None

    def process(self, view_func, fargs, fkwargs):
        return self.view_filter.process(self.next, view_func, fargs, fkwargs)


class ViewFilterChain(object):
    def __init__(self):
        self.chain_head = None
        self.chain_tail = None

    def _find_node(self, name) -> [ViewFilterNode, None]:
        head = self.chain_head
        while head:
            if head.name == name:
                return head
            head = head.next
        return None

    def add_filter(self, view_filter: ViewFilter):
        """Add view filter to the last of chain

        """
        node = ViewFilterNode(view_filter)
        if not self.chain_head:
            self.chain_head = node
        if self.chain_tail:
            self.chain_tail.next = node
        self.chain_tail = node

    def add_filter_after(self, view_filter: ViewFilter, after_filter_name: str):
        """Add view filter after 'after_filter_name'

        """
        target_node = self._find_node(after_filter_name)
        assert target_node, f"ViewFilter {after_filter_name} is not in chain"
        target_next = target_node.next
        new_node = ViewFilterNode(view_filter)
        target_node.next = new_node
        new_node.next = target_next
        if not new_node.next:
            self.chain_tail = new_node

    def process_chain(self, view_func, fargs, fkwargs):
        if self.chain_head:
            return self.chain_head.process(view_func, fargs, fkwargs)
        else:
            return view_func(*fargs, **fkwargs)
