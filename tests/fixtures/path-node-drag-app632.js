  function beginPathNodeDrag(event, commandIndex, handleType, object = pathNodeEdit.object, handleElement = event.currentTarget) {
    if (!object) return;
    resetPaintedVectorDirectSelectionCycle();
    event.preventDefault();
    event.stopPropagation();
    // Pointer gestures start on disposable anchor buttons. Move keyboard focus
    // to the stable canvas viewport so arrows and Escape still edit the point
    // after the overlay replaces those buttons during the drag.
    els.viewport?.focus?.({ preventScroll: true });
    try {
      // The handle itself is recreated on every overlay render. Capture on the
      // stable overlay so a drag stays alive after its button is replaced.
      (els.pathNodeOverlay || event.currentTarget).setPointerCapture?.(event.pointerId);
    } catch (_error) {
      // Synthetic smoke-test pointer events may not have an active pointer capture target.
    }
    if (!pathNodeEditObjects().includes(object)) pathNodeEdit.objects = [object, ...pathNodeEditObjects()];
    pathNodeEdit.object = object;
    const lineEndpoint = isLineVectorObject(object) && handleType === "endpoint";
    const nextHandle = { objectId: pathEditObjectId(object), commandIndex, handleType };
    const existingHandles = selectedPathHandleRefs();
    const currentHandleSelected = existingHandles.some((handle) => samePathHandle(handle, nextHandle));
    const crossObjectSelection = existingHandles.some((handle) => handle.objectId && handle.objectId !== nextHandle.objectId);
    const selectionModifier = Boolean(event.shiftKey || event.metaKey || event.ctrlKey);
    if (!selectionModifier && !currentHandleSelected && directSelectionTextObjects().length) {
      pathNodeEdit.objects = pathNodeEditObjects();
      ensureDirectSelectionCanvasCollection();
    }
    const modifierAddsHandle = selectionModifier
      && handleType === "endpoint"
      && !currentHandleSelected
      && (!lineEndpoint || crossObjectSelection);
    selectPathHandle(object, commandIndex, handleType, {
      additive: modifierAddsHandle,
      preserveExisting: true
    });
    const startPoint = pathHandleCanvasPoint(object, selectedPathHandleDescriptor(object));
    const selectedHandleStarts = selectedPathHandleRefs().map((descriptor) => {
      const handleObject = objectForPathHandleRef(descriptor);
      const handleDescriptor = handleObject
        ? pathHandleDescriptors(handleObject).find((item) => samePathHandle(qualifyPathHandle(handleObject, item), descriptor))
        : null;
      return handleObject && handleDescriptor ? {
        objectId: descriptor.objectId,
        commandIndex: descriptor.commandIndex,
        handleType: descriptor.handleType,
        point: pathHandleCanvasPoint(handleObject, handleDescriptor)
      } : null;
    }).filter(Boolean);
    const lineSnapshots = [...new Set(selectedHandleStarts.map((item) => objectForPathHandleRef(item)).filter(isLineVectorObject))]
      .map((item) => {
        const endpoints = lineVectorEndpoints(item);
        return {
          objectId: pathEditObjectId(item),
          endpoints: cloneManifestValue(endpoints, endpoints),
          sceneEndpoints: cloneManifestValue(lineVectorSceneEndpoints(item, endpoints), null)
        };
      });
    const pathSnapshots = [...new Set(selectedHandleStarts.map((item) => objectForPathHandleRef(item)).filter((item) => item && !isLineVectorObject(item)))]
      .map((item) => ({
        objectId: pathEditObjectId(item),
        path: copyPathCommands(item.path),
        bezierNodeMeta: cloneManifestValue(item.figureStudioBezierNodeMeta, null)
      }));
    const activeDescriptor = selectedPathHandleDescriptor(object);
    const activeNode = activeDescriptor?.handleType === "endpoint" ? activeDescriptor : controlNodeDescriptor(object, activeDescriptor);
    pathNodeEdit.dragging = {
      objectId: pathEditObjectId(object),
      commandIndex,
      handleType,
      dirty: false,
      startPoint,
      lastPoint: startPoint,
      handles: selectedHandleStarts,
      pointerStartPoint: canvas.getScenePoint(event),
      translations: pathBodyDragTranslations(selectedHandleStarts),
      textSnapshots: captureDirectSelectionTextPositions(),
      pointerId: event.pointerId,
      lineSnapshots,
      pathSnapshots,
      initialNodeType: activeNode ? bezierNodeType(object, activeNode) : "corner",
      selectionBefore: existingHandles.map((handle) => ({ ...handle })),
      currentHandleSelected,
      selectionModifier
    };
    const gesture = pathNodeEdit.dragging;
    startPdfPointScreenGesture(gesture, object);
    handleElement.classList.add("dragging");
    handleElement.classList.add("selected");
  }
