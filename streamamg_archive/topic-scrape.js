(async () => {
    const sleep = (ms) => new Promise(r => setTimeout(r, ms));
  
    // 1) Find tree and "Topics"
    const treeRoot =
      document.querySelector('ul.jstree-children[role="group"]') ||
      document.querySelector('[role="tree"]') ||
      document.querySelector('.jstree, .jstree-children');
  
    if (!treeRoot) {
      console.error('❌ Could not find tree root');
      return;
    }
  
    const allAnchors = Array.from(document.querySelectorAll('a.jstree-anchor'));
    const topicsAnchor = allAnchors.find(a => a.textContent.trim() === 'Topics');
    if (!topicsAnchor) {
      console.error('❌ "Topics" not found');
      return;
    }
    const topicsLi = topicsAnchor.closest('li');
  
    // 2) Expand all children under "Topics"
    try {
      const container = topicsLi.closest('.jstree, [role="tree"]') || treeRoot;
      if (window.jQuery && jQuery(container).jstree) {
        const inst = jQuery(container).jstree(true);
        const nodeId = topicsLi.id || topicsAnchor.id || topicsAnchor.getAttribute('id');
        if (nodeId) inst.open_all(nodeId);
        else inst.open_all();
        await sleep(500);
      } else {
        let guard = 0;
        while (topicsLi.querySelector('li.jstree-closed') && guard < 300) {
          topicsLi.querySelectorAll('li.jstree-closed > i.jstree-ocl').forEach(i => {
            i.dispatchEvent(new MouseEvent('click', { bubbles: true }));
          });
          await sleep(200);
          guard++;
        }
      }
    } catch (e) {
      console.warn('⚠️ expand issue:', e);
    }
  
    // 3) Collect breadcrumb paths from Topics
    const pathFromTopics = (anchor) => {
      const parts = [];
      let li = anchor.closest('li');
      while (li) {
        const a = li.querySelector(':scope > a.jstree-anchor');
        if (a) {
          const t = a.textContent.trim();
          parts.unshift(t);
          if (t === 'Topics') break;
        }
        li = li.parentElement?.closest('li') || null;
      }
      return (parts[0] === 'Topics') ? parts : null;
    };
  
    const subtreeAnchors = topicsLi.querySelectorAll('a.jstree-anchor');
    const paths = [];
    const seen = new Set();
    Array.from(subtreeAnchors).forEach(a => {
      const parts = pathFromTopics(a);
      if (parts && parts.length > 1) {
        const str = parts.join('>');
        if (!seen.has(str)) {
          seen.add(str);
          paths.push(parts);
        }
      }
    });
  
    // 4) Build nested array structure
    function insertPath(nodes, parts) {
      let currentLevel = nodes;
      for (let i = 0; i < parts.length; i++) {
        const name = parts[i];
        let node = currentLevel.find(n => n.name === name);
        if (!node) {
          node = { name };
          currentLevel.push(node);
        }
        if (i < parts.length - 1) {
          node.children = node.children || [];
          currentLevel = node.children;
        }
      }
    }
  
    const root = [];
    for (const parts of paths) {
      insertPath(root, parts);
    }
  
    // 5) Download JSON
      const blob = new Blob([JSON.stringify(root, null, 2)], { type: 'application/json' });
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = `topics_tree_array_${Date.now()}.json`;
      document.body.appendChild(a);
      a.click();
      document.body.removeChild(a);
      URL.revokeObjectURL(url);
  
    console.log(`✅ Extracted ${paths.length} items. Nested array JSON downloaded.`);
    window.__topicsArrayTree = root;
  })();
  