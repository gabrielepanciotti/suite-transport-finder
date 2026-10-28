import { Settings } from "lucide-react";
import {
  Button,
  Card,
  CardBody,
  CardHeader,
  CardTitle,
  PageHeader,
} from "@suite/design-system";

export function Impostazioni() {
  return (
    <div className="flex max-w-3xl flex-col gap-6">
      <PageHeader
        icon={<Settings aria-hidden />}
        title="Impostazioni"
        subtitle="Gestione del nodo TransportFinder."
      />
      <Card>
        <CardHeader>
          <CardTitle>Configurazione del nodo</CardTitle>
        </CardHeader>
        <CardBody className="flex flex-col gap-4">
          <p className="text-sm text-muted">
            Le fonti di ricerca e la configurazione tecnica sono gestite nella
            panoramica del nodo.
          </p>
          <Button asChild variant="secondary">
            <a href="/overview">Apri panoramica</a>
          </Button>
        </CardBody>
      </Card>
    </div>
  );
}
