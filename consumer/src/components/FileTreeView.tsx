import { useState } from "react";

interface TreeNode {
  id: string;
  name: string;
  type: "file" | "folder";
  mimeType: string;
  children?: TreeNode[];
  modifiedTime?: string;
  url?: string;
}

interface Props {
  nodes: TreeNode[];
  selectedIds: Set<string>;
  onSelectionChange: (ids: Set<string>) => void;
}

function getAllFileIds(nodes: TreeNode[]): string[] {
  const ids: string[] = [];
  for (const node of nodes) {
    if (node.type === "file") ids.push(node.id);
    if (node.children) ids.push(...getAllFileIds(node.children));
  }
  return ids;
}

function countFiles(nodes: TreeNode[]): number {
  return getAllFileIds(nodes).length;
}

function TreeItem({
  node,
  depth,
  selectedIds,
  onToggle,
  onToggleFolder,
}: {
  node: TreeNode;
  depth: number;
  selectedIds: Set<string>;
  onToggle: (id: string) => void;
  onToggleFolder: (ids: string[], checked: boolean) => void;
}) {
  const [expanded, setExpanded] = useState(true);

  if (node.type === "folder") {
    const childFileIds = getAllFileIds(node.children || []);
    const allSelected = childFileIds.length > 0 && childFileIds.every((id) => selectedIds.has(id));
    const someSelected = childFileIds.some((id) => selectedIds.has(id));

    return (
      <div>
        <div className="tree-item" style={{ paddingLeft: depth * 20 }}>
          <button className="tree-toggle" onClick={() => setExpanded(!expanded)}>
            {expanded ? "▾" : "▸"}
          </button>
          <input
            type="checkbox"
            checked={allSelected}
            ref={(el) => {
              if (el) el.indeterminate = someSelected && !allSelected;
            }}
            onChange={() => onToggleFolder(childFileIds, !allSelected)}
          />
          <span className="tree-icon">📁</span>
          <span className="tree-name">{node.name}</span>
          <span className="tree-count">{childFileIds.length} files</span>
        </div>
        {expanded &&
          node.children?.map((child) => (
            <TreeItem
              key={child.id}
              node={child}
              depth={depth + 1}
              selectedIds={selectedIds}
              onToggle={onToggle}
              onToggleFolder={onToggleFolder}
            />
          ))}
      </div>
    );
  }

  const isDocx = node.mimeType?.includes("wordprocessingml");
  return (
    <div className="tree-item" style={{ paddingLeft: depth * 20 }}>
      <span className="tree-toggle" style={{ visibility: "hidden" }}>▸</span>
      <input
        type="checkbox"
        checked={selectedIds.has(node.id)}
        onChange={() => onToggle(node.id)}
      />
      <span className="tree-icon">{isDocx ? "📝" : "📄"}</span>
      <span className="tree-name">{node.name}</span>
    </div>
  );
}

export default function FileTreeView({ nodes, selectedIds, onSelectionChange }: Props) {
  const allFileIds = getAllFileIds(nodes);
  const allSelected = allFileIds.length > 0 && allFileIds.every((id) => selectedIds.has(id));

  const handleToggle = (id: string) => {
    const next = new Set(selectedIds);
    if (next.has(id)) next.delete(id);
    else next.add(id);
    onSelectionChange(next);
  };

  const handleToggleFolder = (ids: string[], checked: boolean) => {
    const next = new Set(selectedIds);
    for (const id of ids) {
      if (checked) next.add(id);
      else next.delete(id);
    }
    onSelectionChange(next);
  };

  const handleSelectAll = () => {
    if (allSelected) {
      onSelectionChange(new Set());
    } else {
      onSelectionChange(new Set(allFileIds));
    }
  };

  return (
    <div className="file-tree">
      <div className="tree-toolbar">
        <label>
          <input type="checkbox" checked={allSelected} onChange={handleSelectAll} />
          <strong>Select All</strong> ({allFileIds.length} files)
        </label>
        <span className="tree-selected-count">{selectedIds.size} selected</span>
      </div>
      <div className="tree-list">
        {nodes.map((node) => (
          <TreeItem
            key={node.id}
            node={node}
            depth={0}
            selectedIds={selectedIds}
            onToggle={handleToggle}
            onToggleFolder={handleToggleFolder}
          />
        ))}
      </div>
    </div>
  );
}
