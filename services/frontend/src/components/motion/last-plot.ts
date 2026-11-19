// Which plot the visitor opened last. The plot page shows a loading scene while its data streams in; that scene has to
// show the same photo under the same view-transition name as the card that was clicked, or the photo cannot morph.
// A plain module variable: it is only read on the client, during a client-side navigation.
let lastPlotId: string | null = null;

export const rememberPlot = (id: string): void => {
  lastPlotId = id;
};
export const recallPlot = (): string | null => lastPlotId;
