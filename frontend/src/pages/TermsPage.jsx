export default function TermsPage() {
  return (
    <div className="space-y-6 max-w-3xl">
      <h1 className="text-2xl font-bold text-slate-800">Terms of Service</h1>

      <div className="bg-white rounded-xl shadow-sm border border-slate-200 p-6 text-slate-700 space-y-4">
        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            1. Acceptance of Terms
          </h2>
          <p>
            By accessing and using BEEPOS, you accept and agree to be bound by
            these Terms of Service.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            2. Use of Service
          </h2>
          <p>
            You agree to use BEEPOS only for lawful purposes and in accordance
            with these terms. You are responsible for maintaining the security
            of your account.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            3. Payments and Billing
          </h2>
          <p>
            Fees are billed in advance on a monthly or annual basis. Refunds are
            provided only as required by law or as explicitly stated in our
            billing policy.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            4. Limitation of Liability
          </h2>
          <p>
            BEEPOS is provided “as is” without warranties of any kind. We shall
            not be liable for any indirect, incidental, or consequential
            damages.
          </p>
        </section>

        <section>
          <h2 className="text-lg font-semibold text-slate-800 mb-2">
            5. Changes to Terms
          </h2>
          <p>
            We may modify these terms at any time. Continued use of the service
            after changes constitutes acceptance of the new terms.
          </p>
        </section>
      </div>
    </div>
  );
}
