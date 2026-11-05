  function sharedSelectionProperty(selection, property, capabilitiesByObject = null, stylesByObject = null) {
    const eligible = selectionPropertyObjects(property, selection, capabilitiesByObject);
    const characterProperty = ["fill", "fontFamily", "fontSize", "fontWeight", "fontStyle", "underline", "linethrough"].includes(property);
    const values = eligible.flatMap((object) => {
      if (property === "textAlign" && object.figureStudioPptxTextMeta?.schema === "figureStudio.pptxTextLayout.v1") return selectedParagraphIndexes(object).map(index => object.figureStudioPptxTextMeta.paragraphs[index]?.align || object.textAlign || "left");
      if (!characterProperty || !isCanvasTextObject(object) || !object.text) return [selectionPropertyValue(object, property, stylesByObject)];
      const graphemes = scientificTextGraphemes(object);
      const selectedRange = object.isEditing && object.selectionEnd > object.selectionStart;
      const start = selectedRange ? object.selectionStart : 0;
      const end = selectedRange ? object.selectionEnd : graphemes.length;
      return graphemes.slice(start, end).flatMap((grapheme, offset) => {
        if (grapheme === "\n") return [];
        const value = scientificTypographyValueAt(object, start + offset, property);
        return [property === "fontSize" ? displayedTextFontSize(object, value) : value];
      });
    });
    const distinct = new Set(values.map((value) => comparableSelectionValue(value, property)));
    const partial = eligible.length !== selection.length;
    return {
      property,
      value: distinct.size === 1 ? values[0] : null,
      mixed: distinct.size > 1 || partial,
      partial,
      supportedCount: eligible.length,
      totalCount: selection.length
    };
  }
