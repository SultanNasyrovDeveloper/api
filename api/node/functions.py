from surorm.query import function


class GetAncestors(function.DBFunction):
    name = 'fn::get_ancestors'
    args = ('node',)
    body = """
        $ancestor = array::first(
            select id, title
            from node
            where <-(child where in == $node)
        );
        return if $ancestor is not none {
            array::concat(fn::get_ancestors($ancestor.id), [$ancestor])
        } else { return []}
    """


class DeleteSubtree(function.DBFunction):
    name = 'fn::tree::delete_subtree'
    args = ('root',)
    body = """
        $children = (
            select id from node
            where ->(child where out == $root)
        );
        for $child in $children {
            fn::tree::delete_subtree($child.id);
        };
        delete $root;
    """


class GetSubtreeIds(function.JSFunction):
    body = """
        const [node] = arguments;
        const getSubtreeIds = async (root) => {
            const ids = [root];
            const rootChildren = await surrealdb.query(
                'select <-child<-node.id as children from only $id',
                {id: root}
            );
            if (rootChildren && rootChildren.children.length > 0) {
                for (const childId of rootChildren.children) {
                    ids.push(...await getSubtreeIds(childId));
                }
            }
            return ids;
        };
        return await getSubtreeIds(node);
    """
