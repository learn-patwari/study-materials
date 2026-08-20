# Design Principles & Patterns — Interview Prep

> Target: 10–15 YOE · Staff / Senior Engineer
> Companies: Google, Amazon, Uber, Flipkart, Atlassian, JP Morgan, Goldman Sachs

---

## 1. SOLID Principles

### Q1. Single Responsibility Principle (SRP) — real violation and fix.

**Principle:** A class should have only one reason to change.

**Violation — `UserService` doing too much:**
```java
class UserService {
    public void register(User user) {
        // 1. Validate
        if (user.getEmail() == null) throw new IllegalArgumentException("Email required");
        // 2. Persist
        database.save(user);
        // 3. Send email
        emailClient.send(new Email(user.getEmail(), "Welcome!"));
        // 4. Audit log
        auditLog.write("User registered: " + user.getId());
    }
}
// Reason to change: validation rules, DB schema, email template, audit format — all different
```

**Fixed — separate concerns:**
```java
class UserValidator {
    void validate(User user) {
        if (user.getEmail() == null) throw new IllegalArgumentException("Email required");
    }
}

class UserRepository {
    void save(User user) { database.save(user); }
}

class WelcomeEmailSender {
    void send(User user) { emailClient.send(new Email(user.getEmail(), "Welcome!")); }
}

class UserAuditLogger {
    void log(User user) { auditLog.write("User registered: " + user.getId()); }
}

class UserService {
    // Orchestrates — one reason to change: registration workflow
    void register(User user) {
        validator.validate(user);
        repository.save(user);
        emailSender.send(user);
        auditLogger.log(user);
    }
}
```

**Interview nuance:** SRP is about *cohesion*, not literal "one method." A class can have many methods if they all serve the same responsibility. `UserService.register()` and `UserService.updateProfile()` can coexist if they're both "user management workflow."

---

### Q2. Open/Closed Principle (OCP) — new behavior without modifying existing code.

**Principle:** Software entities should be open for extension but closed for modification.

**Violation:**
```java
class DiscountCalculator {
    double calculate(Order order, String type) {
        if (type.equals("STUDENT")) return order.getTotal() * 0.1;
        if (type.equals("SENIOR")) return order.getTotal() * 0.15;
        if (type.equals("VIP")) return order.getTotal() * 0.2;
        return 0; // add new type → modify this class
    }
}
```

**Fixed — extension via polymorphism:**
```java
interface DiscountStrategy {
    double calculate(Order order);
}

class StudentDiscount implements DiscountStrategy {
    public double calculate(Order order) { return order.getTotal() * 0.1; }
}

class SeniorDiscount implements DiscountStrategy {
    public double calculate(Order order) { return order.getTotal() * 0.15; }
}

class VIPDiscount implements DiscountStrategy {
    public double calculate(Order order) { return order.getTotal() * 0.2; }
}

class DiscountCalculator {
    double calculate(Order order, DiscountStrategy strategy) {
        return strategy.calculate(order); // add new type → new class, no modification
    }
}
```

**Java 8+ with functional interfaces:**
```java
Map<String, Function<Order, Double>> discounts = Map.of(
    "STUDENT", order -> order.getTotal() * 0.1,
    "SENIOR",  order -> order.getTotal() * 0.15,
    "VIP",     order -> order.getTotal() * 0.2
);
// Add new type: add entry to map, no class changes
```

---

### Q3. Liskov Substitution Principle (LSP) — the rectangle–square problem.

**Principle:** Objects of a subclass should be replaceable with objects of the parent class without breaking the program.

**Classic violation:**
```java
class Rectangle {
    protected int width, height;
    void setWidth(int w) { this.width = w; }
    void setHeight(int h) { this.height = h; }
    int area() { return width * height; }
}

class Square extends Rectangle {
    @Override
    void setWidth(int w) { this.width = this.height = w; } // breaks Rectangle contract!
    @Override
    void setHeight(int h) { this.width = this.height = h; }
}

// Client code written for Rectangle:
void testArea(Rectangle r) {
    r.setWidth(5);
    r.setHeight(10);
    assert r.area() == 50; // FAILS for Square — area is 100
}
```

**Fix — don't extend if behavior contracts differ:**
```java
interface Shape { int area(); }

class Rectangle implements Shape {
    Rectangle(int width, int height) { ... }
    public int area() { return width * height; }
}

class Square implements Shape {
    Square(int side) { ... }
    public int area() { return side * side; }
}
// No inheritance — client uses Shape interface, LSP satisfied
```

**LSP check:** For every method in the parent class, the subclass must:
1. Accept the same or broader input (contravariance in parameters)
2. Produce the same or narrower output (covariance in return type)
3. Not throw new checked exceptions
4. Maintain the same invariants

---

### Q4. Interface Segregation Principle (ISP) — fat interfaces.

**Principle:** Clients should not be forced to depend on methods they don't use.

**Violation:**
```java
interface Worker {
    void work();
    void eat();
    void sleep();
}

class Robot implements Worker {
    public void work() { /* OK */ }
    public void eat() { throw new UnsupportedOperationException(); } // robots don't eat
    public void sleep() { throw new UnsupportedOperationException(); }
}
```

**Fixed — segregate interfaces:**
```java
interface Workable { void work(); }
interface Eatable  { void eat(); }
interface Sleepable { void sleep(); }

class Human implements Workable, Eatable, Sleepable {
    public void work() { ... }
    public void eat() { ... }
    public void sleep() { ... }
}

class Robot implements Workable {
    public void work() { ... } // only what applies
}
```

**Java real-world example:** `java.util.List` implements `Collection`, `Iterable`, etc. — but a read-only list shouldn't implement `add()`. This is why `Collections.unmodifiableList()` throws `UnsupportedOperationException` — a classic ISP violation in the JDK itself. Modern `List.of()` addresses this differently.

---

### Q5. Dependency Inversion Principle (DIP) — depend on abstractions.

**Principle:** High-level modules should not depend on low-level modules. Both should depend on abstractions.

**Violation:**
```java
class OrderService {
    private MySQLOrderRepository repository = new MySQLOrderRepository(); // tight coupling
    
    void placeOrder(Order order) {
        repository.save(order); // can't swap to MongoDB without changing OrderService
    }
}
```

**Fixed:**
```java
interface OrderRepository {
    void save(Order order);
    Optional<Order> findById(String id);
}

class MySQLOrderRepository implements OrderRepository { ... }
class MongoOrderRepository implements OrderRepository { ... }
class InMemoryOrderRepository implements OrderRepository { ... } // for tests

class OrderService {
    private final OrderRepository repository; // depends on abstraction
    
    OrderService(OrderRepository repository) { // injected — DIP + DI
        this.repository = repository;
    }
    
    void placeOrder(Order order) {
        repository.save(order); // works with any implementation
    }
}
```

**DIP vs Dependency Injection:** DIP is the principle (depend on abstractions). DI is one mechanism to achieve it (inject dependencies). Spring's `@Autowired` + `@Bean` is DI enforcing DIP.

---

## 2. Additional Design Principles

### Q6. DRY, KISS, YAGNI — with Java examples.

**DRY (Don't Repeat Yourself):**
```java
// Violation: same validation duplicated in 3 places
class OrderController {
    void createOrder(String email) {
        if (!email.contains("@")) throw new BadRequestException("Invalid email");
        // ...
    }
    void updateOrder(String email) {
        if (!email.contains("@")) throw new BadRequestException("Invalid email"); // duplicate
    }
}

// Fixed: extract shared logic
class EmailValidator {
    static void validate(String email) {
        if (!email.contains("@")) throw new BadRequestException("Invalid email");
    }
}
```

**KISS (Keep It Simple, Stupid):**
```java
// Over-engineered: generic framework for a one-time use
abstract class AbstractProcessor<T, R> implements Processable<T>, Transformable<R> { ... }

// Simple: just a method
List<String> toUpperCase(List<String> list) {
    return list.stream().map(String::toUpperCase).collect(toList());
}
```

**YAGNI (You Aren't Gonna Need It):**
```java
// YAGNI violation: building plugin system for a feature that may never need plugins
class ReportGenerator {
    List<ReportPlugin> plugins = new ArrayList<>(); // nobody asked for plugins
    void registerPlugin(ReportPlugin p) { ... }
    void generateReport() { ... }
}

// YAGNI correct: build what's needed now; add plugins if/when required
class ReportGenerator {
    String generateReport(ReportConfig config) { ... }
}
```

---

## 3. Creational Patterns

### Q7. Singleton — thread-safe variants.

```java
// 1. Eager initialization (thread-safe — class loading is thread-safe)
class EagerSingleton {
    private static final EagerSingleton INSTANCE = new EagerSingleton();
    private EagerSingleton() {}
    public static EagerSingleton getInstance() { return INSTANCE; }
}

// 2. Double-checked locking (lazy, thread-safe with volatile)
class LazyDCLSingleton {
    private static volatile LazyDCLSingleton instance; // volatile prevents reordering
    private LazyDCLSingleton() {}
    
    public static LazyDCLSingleton getInstance() {
        if (instance == null) {                          // first check (no lock)
            synchronized (LazyDCLSingleton.class) {
                if (instance == null) {                  // second check (with lock)
                    instance = new LazyDCLSingleton();
                }
            }
        }
        return instance;
    }
}

// 3. Initialization-on-demand holder (BEST: lazy, thread-safe, no synchronization overhead)
class HolderSingleton {
    private HolderSingleton() {}
    
    private static class Holder {
        static final HolderSingleton INSTANCE = new HolderSingleton();
    }
    
    public static HolderSingleton getInstance() { return Holder.INSTANCE; }
    // Class loading of Holder is thread-safe by JVM spec — lazy because Holder
    // is only loaded when getInstance() is first called
}

// 4. Enum singleton (simplest, serialization-safe, reflection-safe)
enum EnumSingleton {
    INSTANCE;
    public void doSomething() { ... }
}
EnumSingleton.INSTANCE.doSomething();
```

**Interview follow-up:** How can Singleton be broken?
- Reflection: `constructor.setAccessible(true); constructor.newInstance()` — fix: throw in constructor if instance exists
- Serialization: `readObject()` creates a new instance — fix: implement `readResolve()`
- Multiple classloaders: each ClassLoader gets its own Singleton — rare in modern apps

---

### Q8. Factory Method vs Abstract Factory.

**Factory Method** — one product, subclasses decide the concrete type:
```java
abstract class NotificationService {
    abstract Notification createNotification(); // factory method
    
    void send(String message) {
        Notification n = createNotification(); // uses the factory method
        n.deliver(message);
    }
}

class EmailNotificationService extends NotificationService {
    Notification createNotification() { return new EmailNotification(); }
}

class SMSNotificationService extends NotificationService {
    Notification createNotification() { return new SMSNotification(); }
}
```

**Abstract Factory** — family of related products, one factory per family:
```java
interface UIFactory {
    Button createButton();
    TextBox createTextBox();
    Dropdown createDropdown();
}

class WindowsUIFactory implements UIFactory {
    public Button createButton() { return new WindowsButton(); }
    public TextBox createTextBox() { return new WindowsTextBox(); }
    public Dropdown createDropdown() { return new WindowsDropdown(); }
}

class MacUIFactory implements UIFactory {
    public Button createButton() { return new MacButton(); }
    public TextBox createTextBox() { return new MacTextBox(); }
    public Dropdown createDropdown() { return new MacDropdown(); }
}
// Client uses UIFactory — swap entire family by swapping factory
```

**Key difference:** Factory Method creates one type; Abstract Factory creates a coordinated family of types.

---

### Q9. Builder pattern — when and how.

**When to use:** Object with many optional parameters, complex construction logic, or when you want immutable objects with readable construction.

```java
// Without Builder: telescoping constructor or JavaBean (mutable state risk)
new HttpRequest("GET", "https://api.example.com", null, null, 5000, true, Map.of());

// With Builder:
HttpRequest request = HttpRequest.builder()
    .method("GET")
    .url("https://api.example.com")
    .timeout(5000)
    .followRedirects(true)
    .header("Authorization", "Bearer token")
    .build();

class HttpRequest {
    private final String method;
    private final String url;
    private final int timeout;
    private final boolean followRedirects;
    private final Map<String, String> headers;
    // all final — immutable after build()
    
    private HttpRequest(Builder b) {
        this.method = Objects.requireNonNull(b.method, "method required");
        this.url = Objects.requireNonNull(b.url, "url required");
        this.timeout = b.timeout;
        this.followRedirects = b.followRedirects;
        this.headers = Map.copyOf(b.headers);
    }
    
    public static Builder builder() { return new Builder(); }
    
    public static class Builder {
        private String method;
        private String url;
        private int timeout = 3000; // default
        private boolean followRedirects = true;
        private Map<String, String> headers = new HashMap<>();
        
        public Builder method(String m) { this.method = m; return this; }
        public Builder url(String u) { this.url = u; return this; }
        public Builder timeout(int t) { this.timeout = t; return this; }
        public Builder followRedirects(boolean f) { this.followRedirects = f; return this; }
        public Builder header(String k, String v) { this.headers.put(k, v); return this; }
        public HttpRequest build() { return new HttpRequest(this); }
    }
}
```

**Lombok shortcut:** `@Builder` on the class generates the builder automatically. `@Builder.Default` sets defaults. `@NonNull` validates required fields.

---

### Q10. Prototype pattern — when cloning beats construction.

**When to use:** Object creation is expensive (DB lookup, complex initialization), and you need many similar objects that differ only slightly.

```java
interface Prototype<T> {
    T copy();
}

class ReportTemplate implements Prototype<ReportTemplate> {
    private final List<Section> sections; // expensive to build
    private String title;
    
    // Copy constructor (preferred over Cloneable)
    private ReportTemplate(ReportTemplate other) {
        this.sections = new ArrayList<>(other.sections); // shallow copy — ok if Sections are immutable
        this.title = other.title;
    }
    
    public ReportTemplate copy() { return new ReportTemplate(this); }
    
    public ReportTemplate withTitle(String title) {
        ReportTemplate copy = this.copy();
        copy.title = title;
        return copy;
    }
}

// Usage: clone and customize — no re-fetching from DB
ReportTemplate monthlyTemplate = templateRepository.find("monthly"); // expensive
ReportTemplate januaryReport = monthlyTemplate.withTitle("January 2024");
ReportTemplate februaryReport = monthlyTemplate.withTitle("February 2024");
```

**`Cloneable` gotcha:** `Object.clone()` is shallow. `Cloneable` is a marker interface with no `clone()` method — it's a broken design in Java. Prefer copy constructors or static factory `copy()` methods.

---

## 4. Structural Patterns

### Q11. Decorator pattern — add behavior without subclassing.

**When to use:** Add responsibilities to objects dynamically. Alternative to subclassing when you need combinations of features.

```java
interface DataProcessor {
    String process(String data);
}

class BaseProcessor implements DataProcessor {
    public String process(String data) { return data.trim(); }
}

// Each decorator adds one behavior and wraps another processor
class EncryptionDecorator implements DataProcessor {
    private final DataProcessor wrapped;
    EncryptionDecorator(DataProcessor dp) { this.wrapped = dp; }
    public String process(String data) {
        return encrypt(wrapped.process(data));
    }
}

class CompressionDecorator implements DataProcessor {
    private final DataProcessor wrapped;
    CompressionDecorator(DataProcessor dp) { this.wrapped = dp; }
    public String process(String data) {
        return compress(wrapped.process(data));
    }
}

class LoggingDecorator implements DataProcessor {
    private final DataProcessor wrapped;
    LoggingDecorator(DataProcessor dp) { this.wrapped = dp; }
    public String process(String data) {
        log.info("Processing: " + data.length() + " chars");
        String result = wrapped.process(data);
        log.info("Done: " + result.length() + " chars");
        return result;
    }
}

// Compose at runtime:
DataProcessor processor = new LoggingDecorator(
    new EncryptionDecorator(
        new CompressionDecorator(
            new BaseProcessor()
        )
    )
);
// Same as Java's I/O: new BufferedReader(new FileReader(path))
```

**Java I/O is the canonical Decorator example:** `InputStream → FileInputStream → BufferedInputStream → DataInputStream`

---

### Q12. Proxy pattern — control access to an object.

Three use cases:
1. **Virtual proxy** — lazy initialization (create expensive object only when needed)
2. **Protection proxy** — access control
3. **Remote proxy** — local representative for a remote object (RMI)

```java
interface ImageLoader {
    void display();
}

// Virtual Proxy: expensive image only loaded on first display()
class LazyImageProxy implements ImageLoader {
    private final String filename;
    private RealImage realImage; // null until needed
    
    LazyImageProxy(String filename) { this.filename = filename; }
    
    public void display() {
        if (realImage == null) {
            realImage = new RealImage(filename); // load only when needed
        }
        realImage.display();
    }
}

// Protection Proxy: check permissions before delegating
class SecureImageProxy implements ImageLoader {
    private final RealImage realImage;
    private final User user;
    
    public void display() {
        if (!user.hasPermission("IMAGE_VIEW")) throw new SecurityException();
        realImage.display();
    }
}

// Dynamic Proxy (Java reflection):
ImageLoader proxy = (ImageLoader) Proxy.newProxyInstance(
    ImageLoader.class.getClassLoader(),
    new Class[]{ImageLoader.class},
    (p, method, args) -> {
        System.out.println("Before: " + method.getName());
        Object result = method.invoke(realImage, args);
        System.out.println("After: " + method.getName());
        return result;
    }
);
// This is how Spring AOP works under the hood
```

---

### Q13. Adapter pattern — make incompatible interfaces work together.

```java
// Third-party library with incompatible interface
class LegacyPaymentGateway {
    void processPayment(String cardNumber, int amountInPaise) { ... }
}

// Our application expects:
interface PaymentProcessor {
    void pay(PaymentRequest request);
}

// Adapter bridges the gap:
class LegacyPaymentAdapter implements PaymentProcessor {
    private final LegacyPaymentGateway legacy;
    
    LegacyPaymentAdapter(LegacyPaymentGateway gateway) { this.legacy = gateway; }
    
    public void pay(PaymentRequest request) {
        int amountInPaise = (int)(request.getAmountRupees() * 100);
        legacy.processPayment(request.getCardNumber(), amountInPaise);
    }
}

// Client code only sees PaymentProcessor — unaware of legacy gateway
PaymentProcessor processor = new LegacyPaymentAdapter(new LegacyPaymentGateway());
processor.pay(new PaymentRequest("4111...1111", 999.99));
```

**Real world:** `Arrays.asList()` adapts an array to the `List` interface. `InputStreamReader` adapts `InputStream` (bytes) to `Reader` (chars).

---

### Q14. Facade pattern — simplify a complex subsystem.

```java
// Complex subsystem: order processing involves many services
class FacadeOrderService {
    private final InventoryService inventory;
    private final PaymentService payment;
    private final ShippingService shipping;
    private final NotificationService notification;
    private final AuditService audit;
    
    // Single simple method hides the complexity
    public OrderConfirmation placeOrder(Cart cart, PaymentDetails payment) {
        inventory.reserve(cart.getItems());
        PaymentResult payResult = this.payment.charge(payment, cart.getTotal());
        ShipmentInfo shipment = shipping.schedule(cart.getDeliveryAddress());
        notification.sendConfirmation(cart.getUserEmail(), shipment);
        audit.log("ORDER_PLACED", cart.getUserId());
        return new OrderConfirmation(payResult.getTransactionId(), shipment.getTrackingId());
    }
}
// Client calls one method; Facade orchestrates the subsystem
```

**Facade vs Service Layer:** Often synonymous. In DDD, an Application Service plays the Facade role — it orchestrates domain objects and infrastructure without exposing their complexity.

---

## 5. Behavioral Patterns

### Q15. Strategy pattern — swappable algorithms.

```java
// Different sorting strategies selected at runtime
interface SortStrategy<T> {
    void sort(List<T> list);
}

class QuickSort<T extends Comparable<T>> implements SortStrategy<T> {
    public void sort(List<T> list) { /* quicksort impl */ }
}

class MergeSort<T extends Comparable<T>> implements SortStrategy<T> {
    public void sort(List<T> list) { /* mergesort impl */ }
}

class DataSorter<T extends Comparable<T>> {
    private SortStrategy<T> strategy;
    
    void setStrategy(SortStrategy<T> strategy) { this.strategy = strategy; }
    
    void sort(List<T> data) {
        strategy.sort(data); // delegates — unaware of algorithm details
    }
}

// Java 8+: Strategy == Functional Interface (no boilerplate needed)
Comparator<Employee> byAge = Comparator.comparingInt(Employee::getAge);
Comparator<Employee> bySalary = Comparator.comparingDouble(Employee::getSalary);
employees.sort(byAge); // strategy selected at call site
employees.sort(bySalary);
```

**Strategy pattern IS functional programming:** `Function<T, R>`, `Predicate<T>`, `Comparator<T>` are all strategy interfaces in Java 8+.

---

### Q16. Observer pattern — event-driven communication.

```java
// Core
interface EventListener<T> {
    void onEvent(T event);
}

class EventBus<T> {
    private final List<EventListener<T>> listeners = new CopyOnWriteArrayList<>();
    
    void subscribe(EventListener<T> listener) { listeners.add(listener); }
    void unsubscribe(EventListener<T> listener) { listeners.remove(listener); }
    void publish(T event) { listeners.forEach(l -> l.onEvent(event)); }
}

// Usage:
record OrderPlacedEvent(String orderId, String userId, double total) {}

EventBus<OrderPlacedEvent> orderBus = new EventBus<>();
orderBus.subscribe(event -> inventoryService.reserve(event.orderId()));
orderBus.subscribe(event -> notificationService.send(event.userId()));
orderBus.subscribe(event -> analyticsService.track(event));

orderBus.publish(new OrderPlacedEvent("ORD-123", "USR-456", 999.0));
```

**Java built-ins:** `java.util.Observable` (deprecated), `PropertyChangeListener`. Spring uses `ApplicationEventPublisher` + `@EventListener`.

**Thread safety:** Use `CopyOnWriteArrayList` for listeners (thread-safe iteration, rare mutation). Or use async dispatch with an executor.

---

### Q17. Command pattern — encapsulate operations as objects.

**Use cases:** Undo/redo, queuing operations, auditing, transactional rollback.

```java
interface Command {
    void execute();
    void undo();
}

class TransferMoneyCommand implements Command {
    private final Account from, to;
    private final double amount;
    
    TransferMoneyCommand(Account from, Account to, double amount) {
        this.from = from; this.to = to; this.amount = amount;
    }
    
    public void execute() {
        from.debit(amount);
        to.credit(amount);
    }
    
    public void undo() {
        to.debit(amount);
        from.credit(amount);
    }
}

// Command history for undo:
class CommandExecutor {
    private final Deque<Command> history = new ArrayDeque<>();
    
    void execute(Command cmd) {
        cmd.execute();
        history.push(cmd);
    }
    
    void undo() {
        if (!history.isEmpty()) {
            history.pop().undo();
        }
    }
}
```

---

### Q18. Template Method — define skeleton, let subclasses fill steps.

```java
abstract class DataMigration {
    // Template method: defines the algorithm skeleton
    final void migrate() {
        connect();
        List<Record> data = extractData();
        List<Record> transformed = transformData(data);
        loadData(transformed);
        disconnect();
        notifyComplete();
    }
    
    abstract List<Record> extractData();      // subclass implements
    abstract List<Record> transformData(List<Record> data);
    abstract void loadData(List<Record> data);
    
    // Hooks: optional override
    void notifyComplete() { log.info("Migration complete"); }
    
    private void connect() { /* common connection logic */ }
    private void disconnect() { /* common disconnection logic */ }
}

class MySQLToPostgresMigration extends DataMigration {
    List<Record> extractData() { return mysqlDb.fetchAll(); }
    List<Record> transformData(List<Record> data) { return convertTypes(data); }
    void loadData(List<Record> data) { postgresDb.batchInsert(data); }
}
```

**Template Method vs Strategy:**
- Template Method: algorithm skeleton in base class, steps overridden in subclasses (inheritance-based)
- Strategy: entire algorithm swapped at runtime (composition-based)
- Prefer Strategy in modern Java — avoids the fragile base class problem

---

### Q19. Chain of Responsibility — processing pipeline.

```java
abstract class RequestHandler {
    protected RequestHandler next;
    
    RequestHandler setNext(RequestHandler next) {
        this.next = next;
        return next; // allows chaining: auth.setNext(rateLimit).setNext(business)
    }
    
    abstract void handle(HttpRequest request);
}

class AuthenticationHandler extends RequestHandler {
    void handle(HttpRequest request) {
        if (!isAuthenticated(request)) throw new UnauthorizedException();
        if (next != null) next.handle(request); // pass to next in chain
    }
}

class RateLimitHandler extends RequestHandler {
    void handle(HttpRequest request) {
        if (isRateLimited(request)) throw new TooManyRequestsException();
        if (next != null) next.handle(request);
    }
}

class BusinessLogicHandler extends RequestHandler {
    void handle(HttpRequest request) {
        processBusinessLogic(request);
    }
}

// Setup:
RequestHandler chain = new AuthenticationHandler();
chain.setNext(new RateLimitHandler())
     .setNext(new BusinessLogicHandler());

chain.handle(request); // auth → rate limit → business
```

**This IS how servlet filters work.** Spring's `Filter` chain, Spring Security's `SecurityFilterChain`, and middleware in most frameworks are Chain of Responsibility.

---

## 6. Anti-Patterns & Code Smells

### Q20. God Class — the most common smell in monoliths.

**Smell:** A single class that knows too much and does too much. Often emerges when a "service" accumulates all business logic.

```java
// God class: OrderService doing everything
class OrderService {
    void createOrder(...) { ... }
    void cancelOrder(...) { ... }
    void processPayment(...) { ... }  // payment logic
    void calculateShipping(...) { ... } // shipping logic
    void sendInvoiceEmail(...) { ... } // notification logic
    void updateInventory(...) { ... }  // inventory logic
    void generateReport(...) { ... }   // reporting logic
    // 50 more methods...
}
```

**Fix:** Apply SRP — identify distinct responsibilities and extract to dedicated classes. In DDD, model a rich domain where `Order`, `Payment`, `Shipment` are separate aggregates.

---

### Q21. Other critical code smells.

**Feature Envy:** A method uses more data from another class than its own.
```java
class OrderPrinter {
    void print(Order order) {
        // Using Customer's data more than Order's data = Feature Envy
        System.out.println(order.getCustomer().getName());
        System.out.println(order.getCustomer().getAddress().getStreet());
        System.out.println(order.getCustomer().getAddress().getCity());
    }
    // Fix: move print() to Customer, or create CustomerFormatter
}
```

**Primitive Obsession:** Using primitives where a domain concept should be a class.
```java
// Bad: raw String for everything
void createUser(String name, String email, String phone, String zip) { ... }

// Better: domain types that carry validation
record Email(String value) {
    Email { if (!value.contains("@")) throw new IllegalArgumentException("Invalid email"); }
}
record PhoneNumber(String value) { ... }
void createUser(String name, Email email, PhoneNumber phone, ZipCode zip) { ... }
```

**Shotgun Surgery:** One logical change requires touching many classes.
```java
// Adding a new notification channel (push notifications) requires:
// - EmailService, SMSService, PushService (new file)
// - NotificationRouter (modify)
// - UserPreferences (modify schema)
// - ConfigurationService (modify)
// Fix: introduce a proper abstraction (NotificationChannel interface)
```

**Long Method:** Methods > 20-30 lines are hard to understand and test. Extract to named private methods.

**Magic Numbers:** Use named constants.
```java
if (password.length() < 8) ... // What's 8? MIN_PASSWORD_LENGTH
if (order.getTotal() > 10000) ... // What's 10000? GST_APPLICABLE_THRESHOLD
```

---

## 7. GRASP Principles

### Q22. High Cohesion and Low Coupling.

**High Cohesion:** A class's responsibilities are closely related and focused. Each class does one thing well (related to SRP).

```java
// Low cohesion: mixing concerns
class UserUtils {
    static boolean validateEmail(String email) { ... }
    static void sendEmail(String to, String body) { ... }
    static User fromJson(String json) { ... }
    static String hashPassword(String pw) { ... }
}

// High cohesion: each class focused
class EmailValidator { ... }
class EmailSender { ... }
class UserSerializer { ... }
class PasswordHasher { ... }
```

**Low Coupling:** Classes depend on as few other classes as possible, and only through stable abstractions.

```java
// High coupling: depends on concrete classes
class OrderProcessor {
    MySQLDatabase db = new MySQLDatabase(); // depends on concrete
    SmtpEmailClient email = new SmtpEmailClient(); // depends on concrete
}

// Low coupling: depends on interfaces
class OrderProcessor {
    Database db;       // depends on abstraction
    EmailClient email; // depends on abstraction
    
    OrderProcessor(Database db, EmailClient email) { // injected
        this.db = db; this.email = email;
    }
}
```

---

### Q23. Protected Variations (Information Expert, Indirection).

**Information Expert:** Assign responsibility to the class that has the information needed to fulfill it.
```java
// Wrong: Order calculates its own discount (doesn't have pricing rules)
class OrderController {
    double calculateTotal(Order order) {
        double discount = order.getQuantity() > 10 ? 0.1 : 0;
        return order.getUnitPrice() * order.getQuantity() * (1 - discount);
    }
}

// Right: Order IS the expert — it has all the data
class Order {
    double calculateTotal() {
        double discount = quantity > 10 ? 0.1 : 0;
        return unitPrice * quantity * (1 - discount);
    }
}
```

**Protected Variations (PV):** Identify points of variation or instability and create a stable interface around them.
```java
// Point of variation: payment gateway changes (Razorpay → Stripe → Paytm)
interface PaymentGateway {
    PaymentResult charge(PaymentDetails details);
}
// All code depends on PaymentGateway (stable) — never on concrete gateways (unstable)
// Adding a new gateway: new class implementing PaymentGateway, zero changes elsewhere
```

---

## 8. Rapid-Fire Pattern Recognition

### Q24. Which pattern solves which problem?

| Problem | Pattern | Why |
|---|---|---|
| Need to add logging/caching/security without changing the target class | Decorator or Proxy | Decorator adds behavior; Proxy controls access |
| Select algorithm at runtime | Strategy | Encapsulate algorithm family |
| One change ripples through many classes | Facade or Mediator | Reduce coupling via central point |
| Too many subclasses for every combination of features | Decorator | Compose features instead of inheriting |
| Object creation is expensive; need copies | Prototype | Clone instead of reconstruct |
| Decouple sender from multiple receivers | Observer / Event Bus | Publisher-subscriber |
| Support undo/redo | Command | Store operation + inverse |
| Multiple steps in a fixed sequence | Template Method | Skeleton with hooks |
| Long chain of handlers (auth → rate-limit → business) | Chain of Responsibility | Each handler decides to handle or pass |
| Complex subsystem with many classes | Facade | Simple interface to complex system |
| Create objects without knowing their concrete class | Factory Method | Subclass decides what to create |
| Create families of related objects | Abstract Factory | Factory per product family |
| Need exactly one instance | Singleton | Private constructor + static access |
| Many optional parameters | Builder | Step-by-step construction |
| Incompatible interfaces need to work together | Adapter | Translate one interface to another |

---

### Q25. Design patterns in the Java standard library.

| Pattern | Java Example |
|---|---|
| Singleton | `Runtime.getRuntime()`, `System.console()` |
| Factory Method | `Calendar.getInstance()`, `NumberFormat.getInstance()` |
| Abstract Factory | `DocumentBuilderFactory`, `SAXParserFactory` |
| Builder | `StringBuilder`, `Stream.Builder`, `ProcessBuilder` |
| Prototype | `Object.clone()`, `Arrays.copyOf()` |
| Adapter | `Arrays.asList()`, `InputStreamReader`, `Collections.list()` |
| Decorator | `java.io` streams, `Collections.synchronizedList()` |
| Proxy | `java.lang.reflect.Proxy`, Spring AOP proxies |
| Observer | `java.util.Observer` (deprecated), `EventListener` |
| Strategy | `Comparator`, `Runnable`, all functional interfaces |
| Template Method | `AbstractList.indexOf()`, `AbstractMap.equals()` |
| Command | `Runnable`, `Callable`, `java.awt.event.ActionListener` |
| Iterator | `java.util.Iterator`, `Iterable` |
| Composite | `javax.swing.JComponent`, file system hierarchies |
| Chain of Responsibility | `java.util.logging.Logger.getParent()`, servlet filters |

---

*Total: 25 Q&As across 8 sections.*
*Focus areas by company: SOLID (all companies), Singleton thread-safety (Amazon/Goldman), Observer/Command (Atlassian/Uber), Code smells (Google/Flipkart).*
