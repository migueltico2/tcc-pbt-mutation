import org.pitest.mutationtest.config.PluginServices;
import org.pitest.mutationtest.config.ReportOptions;
import org.pitest.mutationtest.tooling.AnalysisResult;
import org.pitest.mutationtest.tooling.EntryPoint;
import org.pitest.util.Glob;

import java.io.File;
import java.nio.file.Path;
import java.util.Arrays;
import java.util.HashMap;
import java.util.List;

/**
 * Executa o PIT programaticamente (equivalente ao goal mutationCoverage do pitest-maven),
 * usado apenas no ambiente sem acesso ao Maven Central.
 *
 * Uso: java PitRunner <classpath-do-projeto> <targetClasses> <targetTests> <reportDir> <sourceDir>
 * targetTests aceita vários globs separados por vírgula. Propriedades de sistema opcionais:
 * pit.mutators (lista separada por vírgula, padrão DEFAULTS), pit.jvmArgs (argumentos das JVMs
 * auxiliares, separados por espaço; usado para passar -Djqwik.tries.default) e pit.threads.
 */
public class PitRunner {

    public static void main(String[] args) {
        ReportOptions o = new ReportOptions();
        o.setClassPathElements(Arrays.asList(args[0].split(File.pathSeparator)));
        o.setTargetClasses(List.of(args[1]));
        List<java.util.function.Predicate<String>> testes = new java.util.ArrayList<>();
        for (String g : args[2].split(",")) {
            testes.add(new Glob(g.trim()));
        }
        o.setTargetTests(testes);
        o.setReportDir(args[3]);
        o.setSourceDirs(List.of(Path.of(args[4])));
        o.setMutators(Arrays.asList(System.getProperty("pit.mutators", "DEFAULTS").split(",")));
        String jvmArgs = System.getProperty("pit.jvmArgs", "").trim();
        if (!jvmArgs.isEmpty()) {
            o.addChildJVMArgs(Arrays.asList(jvmArgs.split(" ")));
        }
        o.addOutputFormats(List.of("XML", "CSV"));
        o.setFullMutationMatrix(true);
        o.setShouldCreateTimestampedReports(false);
        o.setNumberOfThreads(Integer.parseInt(System.getProperty("pit.threads", "2")));
        o.setTimeoutConstant(4000);
        o.setVerbosity(org.pitest.util.Verbosity.QUIET_WITH_PROGRESS);
        o.setGroupConfig(new org.pitest.testapi.TestGroupConfig());
        AnalysisResult r = new EntryPoint().execute(new File("."), o, PluginServices.makeForContextLoader(), new HashMap<>());
        if (r.getError().isPresent()) {
            r.getError().get().printStackTrace();
            System.exit(1);
        }
    }
}
